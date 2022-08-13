#this file only contains things that should be added to a pre-exsting bashrc file

PS1='\[\e[0;1;3;92m\]\u\[\e[0;92m\]@\[\e[0;1;92m\]\h\[\e[0m\]:\[\e[0;94m\]\w\[\e[0m\]$ \[\e[0m\]' # prompt
stty -ixon # disables ctrl-s freeze 
alias r='sudo su' # alias su root
alias sl="ls" 
alias dc="cd" 
alias l="ls -lha" 
alias ll="ls -lha" 
alias la="ls -a" 

# REQUIRES: cowsay, lolcat(gem install), fortune-mod, neofetch
neofetch --ascii "$(fortune -s | cowsay -f $(ls /usr/share/cowsay/cows/ | shuf -n1))" | lolcat -ats 2500 
