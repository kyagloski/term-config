# SUPER MEGA TMUX CONF FILE

set -g base-index 1

setw -g mouse on

bind-key v split-window -h
bind-key s split-window -v

#control key change
unbind-key C-b
set-option -g prefix C-x #M-x for alt-x


#shift arrow to switch window (added ctrl for the sake of vim)
bind -n S-Left  previous-window
bind -n S-Right next-window
#bind -n C-Left previous-window
#bind -n C-Right next-window

#binds kill session
unbind-key x
bind-key k kill-pane

# Reload tmux config
bind r source-file ~/.tmux.conf

# THEME
set -g status-left ''
set -g status-bg colour233
set -g status-fg white
#set -g window-status-current-bg colour237 #239
#set -g window-status-current-fg white
#set -g window-status-current-attr bold

setw -g window-status-current-format ' #[fg=green]#I#[fg=white]:#W#[fg=green]#F '

#set -g window-status-style 'fg=colour248 bg=colour234 dim'
set -g window-status-current-style 'fg=white bg=colour237 bold'
set -g status-interval 60

set -g status-right-length 50
set -g status-left-length 20

set -g status-right '#[default]#[fg=colour232,bg=colour242] %d/%m #[fg=colour232,bg=colour248] %H:%M:%S '

set-window-option -g xterm-keys on

set -g default-terminal "xterm-256color"
