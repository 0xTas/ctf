<h1 align="center"><a href="https://tryhackme.com/room/islandorchestration">TryHackMe Island Orchestration Room</a></h1>

<h2 align="center"><a href="https://twitter.com/0xTas">Writeup By: 0xTas</a></h2>

<p align="center">
    <a href="https://tryhackme.com/p/0xTas">
        <img alt="0xTas TryHackMe Profile" src="https://tryhackme-badges.s3.amazonaws.com/0xTas.png?"></a>
</p>


<h3 align="center">26 June 2022</h3>

---

## Description

Check out the best tropical islands to visit on your next vacation!

---

## Questions

### What is the flag?

I began by adding the server's IP to my /etc/hosts file as "islands.thm". <br>

Afterwards I ran a full Nmap SYN scan on the server: <br>

`sudo nmap -vv -sC -sV -p- -T4 islands.thm -oA nmap/islands_full` <br>

This scan showed me that there were 3 TCP ports open in total: <br>

> 22/tcp   open  ssh           syn-ack ttl 61 OpenSSH 8.2p1 Ubuntu 4ubuntu0.3 (Ubuntu Linux; protocol 2.0) <br>
> 80/tcp   open  http          syn-ack ttl 59 Apache httpd 2.2.22 ((Ubuntu)) <br>
> 8443/tcp open  ssl/https-alt syn-ack ttl 60 <br>

![Nmap SYN Scan Output](https://i.imgur.com/iXk7Jje.png)

There was a standard Apache webserver, SSH, and some sort of service running over HTTPS on port 8443. <br>
Nmap wasn't sure about what exactly was running on port 8443, but the banner info did provide some hints to what was going on: <br>

![Service Headers Suggest Kubernetes](https://i.imgur.com/vhpV5aq.png)

These headers seemed to suggest something about Kubernetes. <br>
To investigate this further, I visited the endpoint in my browser at https://islands.thm:8443: <br>

![Kubernetes API Server output](https://i.imgur.com/QuzjZvI.png)

This looked like some sort of API output, since it was clearly JSON. <br>
I didn't recognize the output, so I pasted it into Google: <br>

![Kubernetes API confirmed by Google](https://i.imgur.com/dd81Lsw.png)

So this was almost definitely Kubernetes, and furthermore it was probably the main API server, according to the [StackOverflow link](https://stackoverflow.com/questions/62204651/kubernetes-forbidden-user-systemanonymous-cannot-get-path) that I had found. <br>
I didn't have any experience enumerating Kubernetes at that point, so I decided to further enumerate the HTTP webserver first. <br>
<br>
Next I started up a directory scan using a tool that I wrote called [ZenBuster](https://github.com/0xTas/zenbuster). <br>
The tool is similar to Gobuster, but written in Python, a bit slower, and with less features. <br>
But hey, I wrote it! So that's gotta count for something 😅 <br>

`zenbuster --dirs -w /usr/share/wordlists/dirb/common.txt -u islands.thm -O dirs.log` <br>

![ZenBuster Scan is Running](https://i.imgur.com/C4EEOnt.png)

While that scan was running in the background, I went back to my web browser for some more manual enumeration. <br>

When I visited the homepage of the HTTP website I was greeted with a nice picture of a tropical island along with a snippet of info. <br>
I checked the HTML source of the webpage but didn't find anything interesting, so next I clicked on one of the "top 5 islands" links that was in a sidebar to the right of the page: <br>
<br>

![Best Tropical Islands - THe Maldives](https://i.imgur.com/pU2Ulpv.png)

What stood out to me right away about this page was the URL. <br>

> http://islands.thm/?page=maldives.php <br>

When I see a PHP get parameter like this, the first thing I like to check is whether it is vulnerable to local file inclusion, so I did: <br>

> http://islands.thm/?page=../../../../../etc/passwd <br>

![Best Tropical Islands - /etc/passwd](https://i.imgur.com/qeplHe6.png)

To my surprise, it worked! The index.php page parameter was vulnerable to a very simple LFI exploit. <br>

My next instinct was to try reading the server's access.log. If I could poison that log with malicious PHP code in my User-Agent or elsewhere, then I could turn this LFI into RCE very quickly. <br>

> http://islands.thm/?page=../../../../var/log/apache2/access.log <br>

![LFI Exploit -- Not So Fast..](https://i.imgur.com/wXxTbrR.png)

Damn, so it wouldn't be *that* easy. <br>

After that I decided to put together a simple [python script](https://github.com/0xTas/ctf/blob/main/tryhackme/room_island_orchestration/lfi.py) to exploit this vulnerability and automate my enumeration a bit. <br>

![lfi.py Exploit Script](https://i.imgur.com/R4aeioi.png)

My script takes each entry from an [LFI wordlist](https://github.com/0xTas/ctf/blob/main/tryhackme/room_island_orchestration/lfipaths.txt) and tries to exploit the LFI vulnerability to read that file. 
Then, if successful, it separates the file's contents from the rest of the page's HTML, and appends it to a log file for me to review. <br>

I ran the script with the following commands: <br>

`chmod +x lfi.py` <br>
`./lfi.py http://islands.thm /usr/share/wordlists/lfiPaths.txt` <br>

After a minute or so, I had a log file nearly 6000-lines long, full of potentially-interesting system files that were leaked from this server. <br>

![lfi.py Script Output](https://i.imgur.com/NuAUrtN.png)

I sifted through this log file, searching for credentials or really anything that could upgrade my LFI to RCE and gain me a foothold on the box.
Unfortunately, however, I did not end up finding any leads for further compromise in the files that my LFI wordlist had fetched for me.
<br>

I did read through the server's Apache2 configuration file, and confirmed that the access and error logs should reside in '/var/log/apache2/' **IF** they existed, but it seems they did not exist.
<br>
The configuration file itself gave a good reason as to why they likely didn't exist, and when I remembered that this server was probably running Kubernetes, it all made sense: <br>

![/etc/apache2/apache2.conf logs location](https://i.imgur.com/EDuwSPS.png)

The webserver was likely running in a container, and because of that, certain logs and other system files that might normally let you elevate LFI to RCE would not have existed in their traditional fashion. <br>

Realizing this, I decided to move on for the time being, and instead begin learning how to enumerate the Kubernetes service. <br>

At the same time, I checked in on my [ZenBuster scan results](https://github.com/0xTas/ctf/blob/main/tryhackme/room_island_orchestration/dirs.log), but unfortunately it had not found anything interesting or out of the ordinary. <br>

Before heading to Google to research how to enumerate k8s, I started up a Nikto scan just to have some sort of recon runnning in the background: <br>

`nikto -h http://islands.thm` <br>

When this had finished, I noticed that it had also identified the LFI vulnerability in index.php, but aside from that it hadn't found anything else of use to me. <br>

![Nikto Scan Output (Identifies LFI Vuln)](https://i.imgur.com/T47PYH8.png)

Next I went to Google and looked for a resource to learn about enumerating Kubernetes, and luckily I came across this helpful page: [HackTricks - Pentesting Kubernetes](https://book.hacktricks.xyz/cloud-security/pentesting-kubernetes).
<br>
After reading about the [basics of Kubernetes](https://book.hacktricks.xyz/cloud-security/pentesting-kubernetes/kubernetes-basics), which was entirely new to me, I began to read about methods for [enumerating k8s](https://book.hacktricks.xyz/cloud-security/pentesting-kubernetes/kubernetes-enumeration).
<br>

I learned that K8s stores credentials, or "secrets", in weakly-encoded base64, and if I could get ahold of a service account token, I might be able to read those secrets straight from the API server running on port 8443. <br>

Luckily, Hacktricks has a section on where these service-account tokens are usually kept, and I already had LFI on the server. <br>

![HackTricks Kubernetes Service Account Tokens](https://i.imgur.com/XdlHwdP.png)

So with this information, I tried to get ahold of a service-account token by exploiting that website's LFI vulnerability: <br>

> http://islands.thm/?page=../../../../var/run/secrets/kubernetes.io/serviceaccount/token <br>

![Kubernetes Service Account Token via LFI](https://i.imgur.com/7RltmV1.png)

It worked! I had the service account token for the k8s pod that was running this website. Next I had to learn how to use that token to authenticate and communicate with the API server.
<br>

Reading further into the Hacktricks pages, I learned that I could use a tool called [kubectl](https://kubernetes.io/docs/reference/kubectl/cheatsheet/) to interface with the API server from the command-line. <br>

First I needed to install it with: `sudo apt install kubernetes-client`. <br>

Then, it appeared that for each time running the `kubectl` command, I would need to supply the API server's address as well as the service-account token, which was very long. 
Because of this, HackTricks recommends storing the server address and token in environment variables, and then aliasing the boilerplate portion of the command to a single cmd. <br>

So I did this, and then began enumerating the k8s API: <br>

(*Note:* I included the `--insecurre-skip-tls-verify=true` option so that I did not need to bother grabbing the ca.cert file) <br> 

`alias k='kubectl --token=$TOKEN --server=$APISERVER --insecure-skip-tls-verify=true'` <br>

![Kubectl Alias Setup](https://i.imgur.com/pDFFDlb.png)

![Kubectl API Server Enumeration](https://i.imgur.com/QroJa02.png)

![Kubectl API Resources List](https://i.imgur.com/vgwqesj.png)

Success, I was now authenticated and communicating with the API server on port 8443. <br>

From here, I was able to list the weakly-encoded secrets for the current namespace with the following command: <br>

`k get secrets -o yaml` <br>

![Kubernetes Server Secrets (Flag Censored)](https://i.imgur.com/hYPhRVi.png)

To my surprise, the output of this command gave me the flag encoded in base64. <br>

I copied/pasted it, echoed and piped it into `base64 -d`, and received the raw flag, completing this fun enumeration challenge! <br>

![Challenge Complete!](https://i.imgur.com/w2I3Lkn.png)

<br>
> Answer: flag{08be****************************}

---
