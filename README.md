# fritzing-PARTS

this repository is the main part-library of all fritzing-application parts. It includes all needed svgs in the svg folders and the part "fzp"-files in the specific folders.

howto's for parts are:

- [https://learn.sparkfun.com/tutorials/make-your-own-fritzing-parts](https://learn.sparkfun.com/tutorials/make-your-own-fritzing-parts)

- [fritzing learning section link]


the folder structure is very needed for the fritzing-application. so it is neassesary to have every thing in place. that means we want to have user generated parts seperated from contributed libarys from known manufactures and the fritzing core parts. 

the folder structure is prepared for it.
fzp's have to be copied into their remaining folders: 
1. user parts
2. contributed parts
3. core-parts

into the svg folder is a quite similar structure. so the svgs has to go into the right folder for user, contrib and core parts. into the svg-folder you find breadboard, schematic and pcb folders. place the svg for the part into it.

example for user parts:

- fzp -> "user"-folder
- breadboard-svg -> svg/user/breadboard
- schematic-svg -> svg/user/schematic
- pcb-svg -> svg/user/schematic