# class OpticalVideoRipper:
#     """
#     Rip optical video discs (DVD and blu-ray)
#     """

#     def archive_video_disc()

#     def auto_rip() -> None:
#         """ Start the auto ripper"""
#         # Main Portion of script
#         # ls to get the drives and start a proc for each feeding /dev/srx as arg
#         lsOut = subprocess.run('ls /dev/sr*', shell=True, capture_output=True, text=True)
#         drives = lsOut.stdout.split('\n')
#         del drives[-1]
#         # Start process for each dirve in list
#         for drive in drives:
#             Process(target=startRip, args=(drive,)).start()
