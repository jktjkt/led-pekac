# Building on NixOS

```
nix-shell ~/work/cesnet/gerrit/CzechLight/buildroot.nix
cd ~/work/prog/_build/_rpi
...
```

This needs a patched libgphoto2, and that one cannot be easily built on buildroot because autoreconf is a PITA.
Genmerate a tarball via:
```
time nix-shell -p autoconf automake libtool intltool pkgconf libxml2 popt --command 'autoreconf -fi; ./configure; make dist'
```
