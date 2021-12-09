#this file only contains things that should be added to a pre-exsting bashrc file

PS1='\[\e[0;1;3;92m\]\u\[\e[0;92m\]@\[\e[0;1;92m\]\h\[\e[0m\]:\[\e[0;94m\]\w\[\e[0m\]$ \[\e[0m\]' # prompt
stty -ixon # disables ctrl-s freeze 
neofetch --ascii_distro debian
alias subl='"/mnt/s/Program Files/Sublime Text 3/sublime_text.exe"' # alias sublime 
alias arceus='ssh -X USER@DOMAIN' # alias server1 
alias dialga='ssh USER@DOMAIN' # alias server2   
alias r='sudo su -' # alias su root
alias stmux='~/.tmux.sh' # alias tmux script

