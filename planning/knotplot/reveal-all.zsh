#!/bin/zsh -f

echo "Making directories readable and executable..."
find . -type d -print | awk '{printf ("chmod 755 \"%s\"\n", $0);}' | sh

echo "Making all files readable..."
chmod -R ugo+r *


find . -type f -print | grep -i "\.cpp"

echo "Done!"



