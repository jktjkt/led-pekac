# Keys and sensitive stuff

I am lazy, so I'm putting some sensitive crypto stuff into the FW images, but not to git.
Here's how to generate them:

```
cd board/pi-overlay
ssh-keygen -A -f .
```

On the device:
```
iwctl station wlan0 connect BlahBlahBlah
```

Copy `/var/lib/iwd/*`.
