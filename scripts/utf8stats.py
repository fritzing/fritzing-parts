import os
import chardet
import sys


def get_encoding_type(file_path):
    with open(file_path, 'rb') as f:
        rawdata = f.read()
    return chardet.detect(rawdata)['encoding']


def skip(filename):

    skip_files_string = """
        ./obsolete/generic-female-header-rounded_7.fzp
./obsolete/generic-female-header_12.fzp
./obsolete/generic-female-header-rounded_11.fzp
./obsolete/generic-female-header-rounded_6.fzp
./obsolete/generic-female-header-rounded_20.fzp
./obsolete/generic-female-header-rounded_8.fzp
./obsolete/generic-female-header_5.fzp
./obsolete/generic-female-header_2.fzp
./obsolete/generic-female-header_6.fzp
./obsolete/generic-male-header_3.fzp
./obsolete/generic-male-header_4.fzp
./obsolete/Generic female header - metal rounded.fzp
./obsolete/generic-female-header-rounded_4.fzp
./obsolete/generic-female-header-rounded_2.fzp
./obsolete/generic-male-header_9.fzp
./obsolete/generic-female-header_7.fzp
./obsolete/generic-female-header-rounded_3.fzp
./obsolete/generic-male-header_7.fzp
./obsolete/generic-female-header-rounded_16.fzp
./obsolete/generic-male-header_8.fzp
./obsolete/generic-female-header-rounded_14.fzp
./obsolete/generic-male-header_10.fzp
./obsolete/generic-male-header_2.fzp
./obsolete/generic-male-header_5.fzp
./obsolete/generic-male-header_6.fzp
./obsolete/Generic female header.fzp
./obsolete/generic-female-header_3.fzp
./obsolete/generic-female-header-rounded_7.fzp
./obsolete/generic-female-header_8.fzp
./obsolete/generic-female-header-rounded_5.fzp
./obsolete/generic-female-header_16.fzp
./obsolete/generic-female-header_10.fzp
./obsolete/generic-female-header-rounded_10.fzp
./obsolete/Generic male header.fzp
./obsolete/generic-female-header_18.fzp
./obsolete/generic-female-header-rounded_18.fzp
./obsolete/generic-male-header_12.fzp
./obsolete/generic-female-header_4.fzp
./obsolete/generic-male-header_20.fzp
./obsolete/generic-male-header_14.fzp
./obsolete/generic-female-header_20.fzp
./obsolete/generic-male-header_18.fzp
./obsolete/generic-male-header_16.fzp
./obsolete/generic-male-header_11.fzp
./obsolete/thermistor_300mil.fzp
./obsolete/generic-female-header_9.fzp
./obsolete/generic-female-header-rounded_12.fzp
./obsolete/generic-female-header_11.fzp
./obsolete/RFM23BP_83dca743edce69d8624555bae587be66_7.fzp
./obsolete/generic-female-header-rounded_9.fzp
./obsolete/generic-female-header_14.fzp
./obsolete/avr_isp_10_pin.fzp
./obsolete/prefix0000_20f55f90aa18635d44e794080c8bfbf6_9.fzp
./obsolete/trimpot_meggitt_pih.fzp
./core/dquidio.fzp
./core/KA78R05_Low_Dropout_Voltage_Regulator.fzp
./core/SMD_elko_0605.fzp
./core/xl4016_d347983e432b7485814462ea48d5bf18_1.fzp
./core/sparkfun-poweric-adm1087-sc-70.fzp
./core/potentiometer_rotary_9mm_6.fzp
./core/Dagu DGServo 9g header connector (female).fzp
./core/potentiometer_trimmer_6mm_5.fzp
./core/SMD_tantalum_capacitor_D_7343.fzp
./core/capacitor_elko_goldcap_4.0F_92eef0d1d2f548b9db9918a1769107d3_2.fzp
./core/RS_Pro_32_1-row_ab_male.fzp
./core/RS_Pro_32_1-row_straight_female.fzp
./core/mic4576_to263_98ea17460fdaa28f8d6fb0856792dbff_1.fzp
./core/SIM800L_5.fzp
./core/micro-usb_b_horizontal.fzp
./core/mic2171_to263_428b5a4f1a2a4e9650fa890d6eadc123_1.fzp
./core/bareconductive_touchboard.fzp
./core/potentiometer_dial_switch_5.fzp
./core/icl7662 (soic)_ceb3f31b17d1c702d898c345cb9aa959_1.fzp
./core/force_sensor_resistor_circular_05in_5.fzp
./core/SMD_resistor_0805.fzp
./core/icl7660_44fc8a045bba7b5d59c3f73c1e79ff67_1.fzp
./core/st662_d8b963bc77dd4b623cd15dc5ffd12c1a_6.fzp
./core/SN74LVC2G14DBVR_2.fzp
./core/JST-03JQ-BT.fzp
./core/sparkfun-poweric-bd10ka5wf-e2-.fzp
./core/SMD_resistor_0603.fzp
./core/lm2577_to220_1585e1a79523015d3bb04fa3c119ed4b_1.fzp
./core/lm2596_to220_f44cb37d8d6021cdacac7094cee01f17_1.fzp
./core/lm2574_soic_139fde836b26224f66fa149e18beb2eb_2.fzp
./core/SMD_tantalum_capacitor_A_3216.fzp
./core/SMD_elko_0405.fzp
./core/lm2596_to263_2cc7b20badfc99329be65b67ba7adc35_1.fzp
./core/xbee_pro_rf_module.fzp
./core/SMD_tantalum_capacitor_C_6032.fzp
./core/mic4575_to220_606f336f4be80536825ec230d0d79b65_1.fzp
./core/xl4005_dd04c65a74197e075712ad6517003651_1.fzp
./core/aoz3018pi_4b4d7335497bbf379c232d88829b4eaf_1.fzp
./core/mic4576_to220_7ca7aead36ea07c96091208b0122f0cc_1.fzp
./core/SparkFun_MIDI_Shield.fzp
./core/SMD_resistor_1206.fzp
./core/sparkfun-poweric-v_reg_317-smd.fzp
./core/SMD_AD5206.fzp
./core/icl7662 (dip)_b0b26f8cea2efc2a43aad86f232f436b_1.fzp
./core/sparkfun-freqctrl-ds1077-.fzp
./core/potentiometer_slider_5.fzp
./core/lm2576_af865fdbce219b6e1655050c6b30f5cb_10.fzp
./core/icl7660_dip_a69567b07fdd8c38176b0c6f9ef2093f_1.fzp
./core/SMD_resistor_0402.fzp
./core/sparkfun-poweric-v_reg_317-dpack.fzp
./core/xl4015_6b5078816154b8728cafe03e7fce04a5_1.fzp
./core/Arduino-Sensor-Shield-v5_1.fzp
./core/Real_Time_Clock_Module___DS1307_RTC_Breakout_Board.fzp
./core/LTC3105_msop.fzp
./core/sparkfun-sensors-adxl180-.fzp
./core/Calliope_mini_V_1_3.fzp
./core/sparkfun-led-luxeon-smd.fzp
./core/JST-B3P-VH.fzp
./core/SMD_tantalum_capacitor_B_3528.fzp
./core/xbee_usb_mini_adapter.fzp
./core/SparkFun_Soil_Moisture_Sensor.fzp
./core/lm2577_to263_8fc1255a99f187de1e702ceedefc2a0b_1.fzp
./core/Heltec_WiFi_LoRa_32_V2.fzp
./core/lm2576_to220_1dca9729a1f57f4b234b0ac8bb7693a7_3.fzp
./core/bmp180_breakout.fzp
./core/potentiometer_rotary_16mm_5.fzp
./core/potentiometer_trimmer_12mm_5.fzp
./core/Dagu DGServo 9g header (male).fzp
./core/SparkFun Load Sensor Combinator.fzp
./core/thermistor_300mil.fzp
./core/lm2575_to263_5b86049dfb531778c02a1ede4e31e375_1.fzp
./core/HLK-PM12.fzp
./core/dquidio_GPRS.fzp
./core/GSM-Quectel_updateTID_2_v1.3.fzp
./core/aoz3013pi_0671c5779d4831e9bb583672ac1d7afe_1.fzp
./core/SMD_elko_0807.fzp
./core/mic4575_to263_e9f75c5adeaad0de490ebb2c6da6e995_1.fzp
./core/sparkfun-poweric-v_reg_317-sink.fzp
./core/onoffshim_1.fzp
./core/lm2575_f4990627fb40e38fcd573bd74d3d7e4c_2.fzp
./core/CAY17.fzp
./core/JST-VHR-3N.fzp
./core/textile_potentiometer_005.fzp
./svg/obsolete/breadboard/prefix0000_rbrun_41e2db2b27ebc0f7c890cf07e8f6b2f0_3_breadboard.svg
./svg/obsolete/schematic/teensy3.1_6c13f38b332a0aaba71943d2489fc615_6_schematic.svg
./svg/obsolete/icon/prefix0000_rbrun_41e2db2b27ebc0f7c890cf07e8f6b2f0_3_icon.svg
./svg/core/breadboard/raspberry-pi-4B_1_breadboard.svg
./svg/core/breadboard/raspberry_pi_b+_breadboard.svg
./svg/core/breadboard/32mm_8x8_dot_matrix_DIP_16_945mil_breadboard.svg
./svg/core/breadboard/20mm_8x8_dot_matrix_DIP_16_600mil_breadboard.svg
./svg/core/breadboard/rtc_ds3231_breakout_breadboard.svg
./svg/core/breadboard/raspberry_pi2_v1.1_breadboard.svg
./svg/core/breadboard/raspberry_pi_3_rev-1.2.svg
./svg/core/schematic/grove_beginner_kit_schematic.svg
./svg/core/icon/rtc_ds3231_breakout_icon.svg
        """
    skip_files = [os.path.normpath(file) for file in skip_files_string.split('\n') if file]
    normalized_filename = os.path.normpath(filename)
    if normalized_filename in skip_files:
        return True

    return False


def check_file(target, file_extension, encoding_statistic, non_utf8_files):
    if target.endswith(file_extension):
        encoding = "skipped"
        if not skip(target):
            encoding = get_encoding_type(target)
        if encoding not in ["utf-8", "ascii", "skipped"]:
            non_utf8_files.append(target)
        encoding_statistic[encoding] = encoding_statistic.get(encoding, 0) + 1


def search_directory(target, file_extension, encoding_statistic, non_utf8_files):
    for root, dirs, files in os.walk(target):
        for file in files:
            full_file_path = os.path.join(root, file)
            check_file(full_file_path, file_extension, encoding_statistic, non_utf8_files)


def get_file_statistic(target, file_extension):
    encoding_statistic = {}
    non_utf8_files = []

    if os.path.isfile(target):
        check_file(target, file_extension, encoding_statistic, non_utf8_files)
    elif os.path.isdir(target):
        search_directory(target, file_extension, encoding_statistic, non_utf8_files)

    return encoding_statistic, non_utf8_files


def print_statistic(target):
    print("Statistics for fzp files:")
    fzp_statistic, fzp_non_utf8_files = get_file_statistic(target, ".fzp")
    for encoding, count in fzp_statistic.items():
        print(f"Encoding: {encoding}, Count: {count}")

    print("\nNon-UTF8/ASCII fzp files:")
    for file in fzp_non_utf8_files:
        print(file)

    print("\nStatistics for svg files:")
    svg_statistic, svg_non_utf8_files = get_file_statistic(target, ".svg")
    for encoding, count in svg_statistic.items():
        print(f"Encoding: {encoding}, Count: {count}")

    print("\nNon-UTF8/ASCII svg files:")
    for file in svg_non_utf8_files:
        print(file)

    print(f"\nPlease note that ASCII is a subset of UTF-8.")

    return len(fzp_non_utf8_files) + len(svg_non_utf8_files) > 0


# Get target from command line arguments
if len(sys.argv) > 1:
    target = sys.argv[1]
    has_non_utf8_files = print_statistic(target)
    if has_non_utf8_files:
        sys.exit("Error: found files that are not UTF-8 or ASCII encoded.")
else:
    print("Please provide a directory or filename as a parameter.")
