import getopt
import sys
import os
import os.path
import re
import xml.dom.minidom
import xml.dom

# Part of CI tests

def usage():
    print("""
usage:
    connectors_misnumbered.py -d [fzp folder]
    checks that connectors with integer names are correctly mapped to connector numbers
""")


def skip(filename):
    skip_files = [
        "./core/AlphaNumericDisplay-v13.fzp",
        "./core/Arduino_Esplora.fzp",
        "./core/arduinoXbeere.fzp",
        "./core/ArduPilotMega_v15.fzp",
        "./core/Bean_revE.fzp",
        "./core/CAR_RELE_NVF4-2.fzp",
        "./core/din-5_midi_connector.fzp",
        "./core/electromechanical-battery-2-aaa.fzp",
        "./core/electromechanical-battery-2-aa.fzp",
        "./core/ESP8266-Thing-Dev.fzp",
        "./core/grove_beginner_kit.fzp",
        "./core/HiFive1.fzp",
        "./core/jlpcb-089.fzp",
        "./obsolete/kameleon.fzp",
        "./core/LilyPad-XBee-v15.fzp",
        "./core/ludusProtoShieldWireless.fzp",
        "./core/monacor_ltr_110_linetransformer.fzp",
        "./core/MyoWare_Proto_Shield.fzp",
        "./core/pinoccio-proto.fzp",
        "./core/Power Screwshield 1.0a.fzp",
        "./core/ProtoShield-Mini-v12.fzp",
        "./core/RN41-v14.fzp",
        "./core/Rotoshield-1.0a.fzp",
        "./core/SMD_BC847.fzp",
        "./core/SMD_BC857.fzp",
        "./core/Sony_Spresense_ext_board_1.fzp",
        "./core/SonySpresenseExtension_CXD5602PWBEXT1.fzp",
        "./core/sparkfun-connectors-db25-hp.fzp",
        "./core/sparkfun-connectors-db25-vp.fzp",
        "./core/sparkfun-connectors-db9-female.fzp",
        "./core/sparkfun-connectors-db9-male.fzp",
        "./core/sparkfun-connectors-din7-.fzp",
        "./core/sparkfun-connectors-f25-hp.fzp",
        "./core/sparkfun-connectors-f25-vp.fzp",
        "./core/sparkfun-connectors-ftdi_basic-pth.fzp",
        "./core/sparkfun-connectors-m02-4ucon-15767.fzp",
        "./core/sparkfun-connectors-m02--jst-2mm-smt.fzp",
        "./core/sparkfun-connectors-m02-rocker.fzp",
        "./core/sparkfun-connectors-m03-.fzp",
        "./core/sparkfun-connectors-m03-smd.fzp",
        "./core/sparkfun-connectors-m04-smd2.fzp",
        "./core/sparkfun-connectors-m05-smd2.fzp",
        "./core/sparkfun-connectors-m05-smd.fzp",
        "./core/sparkfun-connectors-m06-em406.fzp",
        "./core/sparkfun-connectors-m06-smdf.fzp",
        "./core/sparkfun-connectors-m06-smd-straight-combo.fzp",
        "./core/sparkfun-connectors-m08-smd-combo.fzp",
        "./core/sparkfun-displays-7-segment-4digit-for_pogobed_only.fzp",
        "./core/sparkfun-displays-7-segment-4digit-pth.fzp",
        "./core/sparkfun-electromechanical-ayz0202-.fzp",
        "./core/sparkfun-electromechanical-relay-2-g5q.fzp",
        "./core/sparkfun-electromechanical-switch-dpdt-eg2211.fzp",
        "./core/sparkfun-electromechanical-switch-dpdt-es.fzp",
        "./core/sparkfun-electromechanical-switch-dpdt-gpi.fzp",
        "./core/sparkfun-electromechanical-switch-dpdt-pth.fzp",
        "./core/sparkfun-electromechanical-switch-momentary-2-12mm.fzp",
        "./core/sparkfun-electromechanical-switch-momentary-2-.fzp",
        "./core/sparkfun-electromechanical-switch-momentary-2-pth.fzp",
        "./core/sparkfun-electromechanical-switch-momentary-2-smd-2.fzp",
        "./core/sparkfun-electromechanical-switch-momentary-2-smd.fzp",
        "./core/sparkfun-electromechanical-switch-sp3t-.fzp",
        "./core/sparkfun-freqctrl-crystal-5x3.fzp",
        "./core/sparkfun-freqctrl-crystal-epsonmc146.fzp",
        "./core/sparkfun-freqctrl-resonator_nocap-.fzp",
        "./core/sparkfun-led-led_ring-.fzp",
        "./core/SparkFun Load Sensor Combinator.fzp",
        "./core/sparkfun-passives-cap_adj-smd.fzp",
        "./core/sparkfun-passives-fuse-x20mm.fzp",
        "./core/sparkfun-passives-inductor-sru5028.fzp",
        "./core/sparkfun-poweric-transformer-smd.fzp",
        "./core/sparkfun-rf-mirf-.fzp",
        "./core/sx1509-breakout.fzp",
        "./core/Wireless_SD_v3.fzp",
        "./obsolete/sparkfun-electromechanical-battery-2-aaa.fzp",
        "./obsolete/sparkfun-electromechanical-battery-2-aa.fzp",
    ]
    for i, item in enumerate(skip_files):
        skip_files[i] = os.path.normpath(item)
    return os.path.normpath(filename) in skip_files

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hd:", ["help", "directory"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err))  # will print something like "option -a not recognized"
        usage()
        return -1

    dir = None

    for o, a in opts:
        # print o
        # print a
        if o in ("-d", "--directory"):
            dir = a
        elif o in ("-h", "--help"):
            usage()
            return 0
        else:
            assert False, "unhandled option"

    if(not(dir)):
        usage()
        return -1

    pattern = r'(\d+)'
    numberFinder = re.compile(pattern, re.IGNORECASE)

    ret = 0
    count = 0
    for root, dirs, files in os.walk(dir, topdown=False):
        for filename in files:
            if not filename.endswith(".fzp"):
                continue

            fzpFilename = os.path.join(root, filename)
            if skip(fzpFilename):
                continue

            count += 1

            try:
                dom = xml.dom.minidom.parse(fzpFilename)
            except xml.parsers.expat.ExpatError as err:
                print(str(err), fzpFilename)
                continue

            fzp = dom.documentElement
            connectors = fzp.getElementsByTagName("connector")
            gotInt = False
            for connector in connectors:
                try:
                    intname = int(connector.getAttribute("name"))
                    gotInt = True
                except:
                    continue

            if not gotInt:
                continue

            idZero = False
            for connector in connectors:
                try:
                    id = connector.getAttribute("id")
                    match = numberFinder.search(id)
                    if match == None:
                        continue

                    if match.group(1) == '0':
                        idZero = True
                        break
                except:
                    continue

            nameZero = False
            for connector in connectors:
                if connector.getAttribute("name") == "0":
                    nameZero = True
                    break

            mismatches = []
            for connector in connectors:
                idInt = 0
                nameInt = 0
                try:
                    id = connector.getAttribute("id")
                    match = numberFinder.search(id)
                    if match == None:
                        continue

                    idInt = int(match.group(1))
                    nameInt = int(connector.getAttribute("name"))

                except:
                    continue

                mismatch = False
                if nameZero and idZero:
                    mismatch = (idInt != nameInt)
                elif nameZero:
                    mismatch = (idInt != nameInt + 1)
                elif idZero:
                    mismatch = (idInt + 1 != nameInt)
                else:
                    mismatch = (idInt != nameInt)
                if mismatch:
                    mismatches.append(connector)

            if len(mismatches) > 0:
                ret = -1
                print(fzpFilename, nameZero, idZero)
                for connector in mismatches:
                    strings = connector.toxml().split("\n")
                    print(strings[0])
                print()

    if count == 0:
        print("No files checked in ", dir)
        ret = -2
    else:
        print("%s files checked" % count)

    return ret


if __name__ == "__main__":
    sys.exit(main())
