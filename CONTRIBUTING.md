# Contributing a new part

Fork and clone the repository:

    git clone git@github.com:your-username/fritzing-parts.git

Create a branch for the part you want to contribute:

    git branch your-part
    git checkout your-part

Create the fzp file.  
Create the breadboard, schematic and pcb svg files.  

## FZPZ
Fzpz are ment to transfer parts between fritzing users.
Fritzing cannot work with fzpz-parts in its folder-structure.

You have to extract the fzpz:

### fzpzclean-script:
You can use a simple python clean script to split the fzpz:
https://github.com/fritzing/fritzing-parts/blob/master/part-gen-scripts/misc_scripts/fzpzclean.py
*howto is in the script*

### Handwork
*will follow soon*
    
    
## Pull-Request
Please put the svgs and the fzp-file, in the belonging directories:

- fzp -> core-folder
- breadboard svg -> svg/breadboard/ 
- schematic svg -> svg/schematic/ 
- pcb svg -> svg/pcb/ 

All parts has to have a resonable svg for each view.
We need to have a consistent database of parts.

Thanks for contributing. 

Push to your fork and [submit a pull request](https://github.com/fritzing/fritzing-parts/compare/)

# Contributing a fix
fritzing has an obsolete mechanism. 
*will follow soon*

