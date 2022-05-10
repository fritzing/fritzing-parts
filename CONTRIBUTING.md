## How to contribute a new part

1. Fork and clone the repository:

        git clone git@github.com:your-username/fritzing-parts.git

2. Create a branch for the part you want to contribute:

        git branch your-part
        git checkout your-part

3. Place the `.fzp` file in the core folder and the related `.svg` in the view-specific folders:

        partname.fzp -> core/
        partname_icon.svg -> svg/core/icon/
        partname_breadboard.svg -> svg/core/breadboard/ 
        partname_schematic.svg -> svg/core/schematic/ 
        partname_pcb.svg -> svg/core/pcb/ 
        
   *if the partname is allready used see the obsolete parts-instructions*

   See below for exporting your `.fzpz` file to the correct structure.  
   
   You may also find the separate files in your home directory (e.g. `C:\Users\<user>\Documents\Fritzing\parts\user\`; `C:\Users\<user>\Documents\Fritzing\parts\svg\user\`) after you saved the part with the editor.


4. Then test and push!  
   *please commit your pull-requests to the develop branch*

    In order to make Fritzing recognize the new part, run Fritzing and select _Part > Rebuild parts database..._. The part will now be included in the database/index, and become available in the library window.

## How to export your part from within Fritzing (FZPZ)

If you created your part inside the Fritzing app, you will first need to export it and then extract it into the correct structure:

1. Export a `.fzpz` bundle of the part:

   Find the part in the parts library, right-click it and select _Export Part..._

2. Extract the `.fzpz`:

   First, make sure the filename is a good and concise description of your part. If not, rename it.

   Use the [fzpzclean.py python script](https://github.com/fritzing/fritzing-parts/blob/master/scripts/fzpzclean.py) to extract the bundle into the proper structure
   
       python fzpzclean.py -f <folder-with-fzpzs> -d <fritzing-parts-folder> -o core -r

3. Give it a unique **moduleId**

   Since you now have the same part twice, they will have conflicting IDs. In the first line of the `.fzp` file, find the property `moduleId` and change it to something unique. Usually, the full part name will do (without spaces).
   

## How to make your part visible in the part library window

This is optional, because even if your part is not directly visible in one of the bins, it is still accessible via the search and as alternative to similar parts (via a property change).

Open the corresponding "bin" file, for example `bins/core.fzb` for the Core library bin. Then simply add an entry at the position where you want your part to be shown, for example:

    <instance moduleIdRef="ResistorModuleID" modelIndex="3" path=":/resources/parts/core/resistor.fzp">
        <views>
          <iconView layer="icon">
            <geometry z="-1" x="-1" y="-1"></geometry>
          </iconView>
        </views>
    </instance>
    
Note that the `modelIndex` property has no meaning. All that matters is the `moduleIdRef` and `path`.

## How to contribute a fix

Fritzing has an update mechanism. 
When loading a project, Fritzing will check if updates for any of the project parts are available,
and ask if the parts should be replaced with the newer version.
Minor fixes should be done without replacing the part.
Minor changes could be: Fix spelling errors in labels, improve display elements in the graphics (not the connectors), color changes
Fixes and changes that might break a project should make use of the update mechanism.
Breaking changes could be: swapping RX/TX, replacing an obsolete part with a currently available one, add missing connections.
Also note that identical replacement parts could have subtile changes, like a new I2C address. In any of those cases, use the update mechanism.

To use the update mechanism:
The new part should have a different file name (TODO: check if that is really necessary)
The old part should be moved to the obsolete folder if it is not available anymore, or if it has severe errors.
Do not change the moduleId of the old part. The new part should have a new moduleId, for example by adding
a hash to the part name, or using a different has.
Add a 'replacedby' attribute to the version tag of the old part. The attribute value should be the new parts ID:
'''<version replacedby='PCF8574A_f92705dc5bbcb278fb8f55ff08c7872a_1'>4</version>'''

Update the Fritzing database, and test that everything works by loading a fritzing project that uses the old part.
Fritzing should then ask if you want to replace the part. Answer no, and check that the project can be loaded like
before. Then, close the project, do not save it. When you load it again, Fritzing should ask again. This time,
answer yes, and check that the part was properly replaced.


## Advanced part makers: Manual part creation

See the [part file format reference](https://github.com/fritzing/fritzing-app/wiki/2.1-Part-file-format) for a detailed description.



