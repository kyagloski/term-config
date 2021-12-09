#!/bin/sh
tmux \
	new-session -d 'ssh *USER@DOMAIN*' \; \
	send-keys 'sleep 2; bpytop' C-m \; \
	split-window -h 'ssh *USER@DOMAIN*' \; \
	send-keys 'glances' C-m \; \
	send-keys '*PASSWORD*' C-m \; \
	split-window -v '*USER@DOMAIN*' \; \
	send-keys 'sleep 1; htop' C-m \; \
	select-pane -t 0 \; \
	new-window \; \
	send-keys '*USER@DOMAIN*' C-m \; \
	send-keys 'clear; bash' C-m \; \
	new-window \;
tmux select-window -t 1
tmux -2 attach-session -d

