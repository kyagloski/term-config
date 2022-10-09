#!/bin/bash
set -x
if [ $EUID != 0 ]; then
    sudo "$0" "$@"
    exit $?
fi

<<comment
preliminary steps:
    -grab vpn configs (/srv/vpn/net-vpn.ovpn)
    -setup hotkeys
    -setup LVM

    -current keybinds
        navigation
            Move to workspace on the left - Disabled
            Move to workspace on the right - Disabled
        sound and media
            Next Track - Ctrl+.
            Play(or play/pause) - Ctrl+/
            Previous track - Ctrl+,
        system
            Show the overview - Alt+Space
        windows
            Active the window menu - Disabled
            Hide window - Ctrl+Alt+Down
            Maximize window - Ctrl+Alt+Up
            View split on left - Ctrl+Alt+Left
            View split on right - Ctrl+Alt+Right
comment

echo "variables"
user="kyle"
#system_type="server"
system_type="workstation"

echo "remove nonsense"
rm -rf /home/$user/Desktop  
rm -rf /home/$user/Documents  
rm -rf /home/$user/Downloads  
rm -rf /home/$user/Music  
rm -rf /home/$user/Pictures  
rm -rf /home/$user/Public  
rm -rf /home/$user/snap  
rm -rf /home/$user/Templates  
rm -rf /home/$user/Videos

echo "basics"
apt update
ubuntu-drivers devices
ubuntu-drivers autoinstall
apt -y install vim git tmux openvpn neofetch

neofetch
sed -i '/info "Packages" packages/c\#info "Packages" packages' /home/$user/.config/neofetch/config.conf

echo "setup ssh"
su -c "ssh-keygen -q -t rsa -N '' <<< $'\ny' >/dev/null 2>&1" $user

echo "chrome"
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt -y install ./google-chrome-stable_current_amd64.deb
rm google-chrome-stable_current_amd64.deb

if [[ "$system_type" = "workstation" ]]; then
    apt -y install vlc gnome-tweaks gnome-shell-extensions gparted flatpak 

    echo "gwe"
    flatpak --user remote-add --if-not-exists -y flathub https://flathub.org/repo/flathub.flatpakrepo
    flatpak --user install -y flathub com.leinardi.gwe
    flatpak update -y

    echo "discord"
    snap install discord

    git clone https://github.com/daniruiz/flat-remix-gtk.git
    git clone https://github.com/daniruiz/flat-remix-gnome.git
    mv flat-remix-gtk/themes/* /usr/share/themes
    rm -rf flat-remix-gtk
    mv flat-remix-gnome/themes/* /usr/share/themes
    rm -rf flat-remix-gnome

    echo "fonts"
    wget https://github.com/tonsky/FiraCode/releases/download/6.2/Fira_Code_v6.2.zip
    unzip Fira_Code_v6.2.zip -d fira
    mv fira/ttf /usr/local/share/fonts/fira
    rm Fira_Code_v6.2.zip
    rm -rf fira
fi

if [[ "$system_type" = "server" ]]; then
    apt -y install openssh-server
fi

echo "vm"
# https://github.com/QaidVoid/Complete-Single-GPU-Passthrough
apt -y install qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils virt-manager

adduser $user libvirt
systemctl enable libvirtd

echo "install conf"
wget https://github.com/kyagloski/term-config/archive/refs/heads/master.zip
unzip master.zip

mv term-config-master/conf/grub /etc/default/grub
grub-mkconfig -o /boot/grub/grub.cfg
mv term-config-master/conf/vimrc /home/$user/.vimrc
mv term-config-master/conf/tmux.conf /home/$user/.tmux.conf
cp /home/$user/.bashrc /home/$user/.bashrc_default
cat term-config-master/conf/bashrc >> /home/$user/.bashrc
tar -xf term-config-master/cursor.tar.gz -C /usr/share/icons/
rm -rf term-config-master
rm master.zip

# fix wifi power management
sed -i '/wifi.powersave/c\wifi.powersave = 2' /etc/NetworkManager/conf.d/default-wifi-powersave-on.conf

set +x 
echo "the computer will now reboot, is this ok y/n?"
read choice
if [[ "$choice" = "y" ]]; then
    reboot
else
    echo "ok fine, but you really should reboot"
fi
