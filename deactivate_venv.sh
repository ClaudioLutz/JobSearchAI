#!/bin/bash

# Unset VIRTUAL_ENV
unset VIRTUAL_ENV

# Remove virtual environment bin directory from PATH
if [[ ":$PATH:" == *":$VIRTUAL_ENV/bin:"* ]]; then
    export PATH=${PATH//$VIRTUAL_ENV\/bin:/}
fi

if [[ ":$PATH:" == *":$VIRTUAL_ENV/Scripts:"* ]]; then
    export PATH=${PATH//$VIRTUAL_ENV\/Scripts:/}
fi

# Remove (venv) from PS1 - handle different possible formats
if [[ "$PS1" == *"(venv)"* ]]; then
    export PS1=$(echo "$PS1" | sed 's/(venv) //g')
fi

if [[ "$PS1" == *"((venv) )"* ]]; then
    export PS1=$(echo "$PS1" | sed 's/((venv) )//g')
fi

echo "Virtual environment has been deactivated."
echo "Current Python: $(which python)"
echo "To fully deactivate in VS Code, you may need to restart your terminal."
