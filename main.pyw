import mmap
import numpy as np
import tkinter as tk
from exceptions import *
from getpass import getuser
from tkinter.filedialog import askdirectory
from tkinter import messagebox

STR_LEN = 24 # bytes
FRS_SIZE = 1
COAM_SIZE = 4

EMPTY = 0x0

APGD_FIRST_PILOT_OFFSET = 0x7B0D
APGD_SECOND_PILOT_OFFSET = 0x69
APGD_AC_NAME_OFFSET = 0x9
APGD_COAM_OFFSET = 0x7B50
GAMEDAT_PILOT_OFFSET = 0x5
GAMEDAT_AC_NAME_OFFSET = 0x45
GAMEDAT_COAM_OFFSET = 0x108

APGD_COCKPIT_COLOR_OFFSET = 0x7adb #0-22

APGD_COLLARED_RANK = 0x7b4e #1-31

FRS_MEMORY_BANKS_OFFSET = 0x12E #7 banks with 4 slots each, 1 spot between banks

FRS_MEMORY_OFFSET = 0x793F # Only appears in APGD.dat

def str_to_bytes(name):
  hex_name = []
  for x in name[:12]: # AC and Pilot names can only be 12 characters in length
    hex_name.append(int(ord(x)))
    hex_name.append(EMPTY)
  while len(hex_name) < STR_LEN:
    hex_name.append(EMPTY)
  return bytes(hex_name)

def int_to_intX(val, size):
  val = int(val)
  if size == 32:
    if val > 999999999:
      raise OverByte('COAM cannot be larger than 999999999!')
    val = np.int32(val)
  elif size == 8:
    if val > 255:
      raise OverByte('FRS Memory cannot be larger than 255!')
    val = np.int8(val)
  val = np.array(val, dtype=val.dtype)
  val.byteswap(True) # Convert from little-endian to big-endian
  return val

def write_APGD(val, APGD, int_size, offsets):
  if int_size:
    val = int_to_intX(val, int_size)
  else:
    val = str_to_bytes(val)
  with open(APGD, 'r+b') as file:
    mm = mmap.mmap(file.fileno(), 0)
    for offset in offsets:
      mm.seek(offset)
      mm.write(val)

def write_GAMEDAT(val, GAMEDAT, int_size, offsets):
  if int_size:
    val = int_to_intX(val, int_size)
  else:
    val = str_to_bytes(val)
  with open(GAMEDAT, 'r+b') as file:
    mm = mmap.mmap(file.fileno(), 0)
    for offset in offsets:
      mm.seek(offset)
      mm.write(val)

def read_data(APGD):
  pilot = ac = coam = frs = temp = ''
  with open(APGD, 'r+b') as file_APGD:
    mm = mmap.mmap(file_APGD.fileno(), 0)
    mm.seek(APGD_FIRST_PILOT_OFFSET)
    pilot = (mm.read(STR_LEN)).decode('utf-8')
    for x in range(0, STR_LEN, 2):
      temp += pilot[x]
    pilot = temp
    mm.seek(APGD_AC_NAME_OFFSET)
    ac = (mm.read(STR_LEN)).decode('utf-8')
    temp = ''
    for x in range(0, STR_LEN, 2):
      temp += ac[x]
    ac = temp
    mm.seek(APGD_COAM_OFFSET)
    coam = mm.read(COAM_SIZE)
    coam = str(int.from_bytes(coam, "big"))
    mm.seek(FRS_MEMORY_OFFSET)
    frs = mm.read(FRS_SIZE)
    frs = str(int.from_bytes(frs, "big"))
    mm.seek(APGD_COCKPIT_COLOR_OFFSET)
    cockpit = mm.read(FRS_SIZE)
    cockpit = str(int.from_bytes(cockpit, "big"))
    mm.seek(APGD_COLLARED_RANK)
    rank = mm.read(FRS_SIZE)
    rank = str(int.from_bytes(rank, "big"))
  return (pilot, ac, coam, frs, cockpit, rank)


def apply(pilot, ac, coam, frs, APGD, GAMEDAT, MAX_TUNE, COCKPIT, RANK):
  try:
    if pilot != '':
      write_APGD(pilot, APGD, int_size=0, offsets=[APGD_FIRST_PILOT_OFFSET, APGD_SECOND_PILOT_OFFSET])
      write_GAMEDAT(pilot, GAMEDAT, int_size=0, offsets=[GAMEDAT_PILOT_OFFSET])
    if ac != '':
      write_APGD(ac, APGD, int_size=0, offsets=[APGD_AC_NAME_OFFSET])
      write_GAMEDAT(ac, GAMEDAT, int_size=0, offsets=[GAMEDAT_AC_NAME_OFFSET])
    if coam != '':
      write_APGD(coam, APGD, int_size=32, offsets=[APGD_COAM_OFFSET])
      write_GAMEDAT(coam, GAMEDAT, int_size=32, offsets=[GAMEDAT_COAM_OFFSET])
    if frs != '':
      write_APGD(frs, APGD, int_size=8, offsets=[FRS_MEMORY_OFFSET])
    if COCKPIT != '':
      c = int(COCKPIT)
      if c >= 0 and c <= 22:
        write_APGD(c, APGD, int_size=8, offsets=[APGD_COCKPIT_COLOR_OFFSET])
      else:
        raise OverByte("Cockpit Theme Number C must fit 0 <= C <= 22!")
    if RANK != '':
      r = int(RANK)
      if r > 0 and r <= 31:
        write_APGD(r, APGD, int_size=8, offsets=[APGD_COLLARED_RANK])
      else:
        raise OverByte("Collared Rank R must fit 1 <= R <= 31!")
    if MAX_TUNE.get():
      frs_offset = FRS_MEMORY_BANKS_OFFSET
      for bank in range(28):
        write_APGD(255, APGD, int_size=8, offsets=[frs_offset + bank])
    tk.messagebox.showinfo('Success!', 'Applied all changes!')
  except Exception as err:
    tk.messagebox.showinfo("Error", err)

def init_ui(window, root_dir):
  MAX_TUNE = tk.IntVar()
  window.title('ACFA Save Editor')
  tk.Label(window, text='Pilot name: ').grid(row=0)
  tk.Label(window, text='AC name: ').grid(row=1)
  tk.Label(window, text='COAM (money): ').grid(row=2)
  tk.Label(window, text='FRS Memory: ').grid(row=3)
  tk.Label(window, text='Cockpit Theme #(0-22): ').grid(row=4)
  tk.Label(window, text='Collared Rank (1-31): ').grid(row=5)
  tk.Checkbutton(window, text="Max Tune?", variable=MAX_TUNE).grid(row=6)
  e_p_name = tk.Entry(window)
  e_p_name.grid(row=0, column=1)
  e_ac_name = tk.Entry(window)
  e_ac_name.grid(row=1, column=1)
  e_coam = tk.Entry(window)
  e_coam.grid(row=2, column=1)
  e_frs_memory = tk.Entry(window)
  e_frs_memory.grid(row=3, column=1)
  e_cockpit = tk.Entry(window)
  e_cockpit.grid(row=4, column=1)
  e_rank = tk.Entry(window)
  e_rank.grid(row=5, column=1)
  messagebox.showinfo('Open Save Folder', 'Ex: GAMEDATXXXX')
  directory = askdirectory(initialdir=root_dir)
  APGD = directory + '/APGD.dat'
  GAMEDAT = directory + '/' + directory.split('/')[-1] + '_CONTENT'
  p, a, c, f, cockpit, rank = read_data(APGD)
  e_p_name.insert(0, p)
  e_ac_name.insert(0, a)
  e_coam.insert(0, c)
  e_frs_memory.insert(0, f)
  e_cockpit.insert(0, cockpit)
  e_rank.insert(0, rank)
  b_apply = tk.Button(window, text='Apply', width=10, command=lambda: apply(e_p_name.get(), e_ac_name.get(), e_coam.get(), e_frs_memory.get(), APGD, GAMEDAT, MAX_TUNE, e_cockpit.get(), e_rank.get())).grid(row=7, column=0)
  b_quit = tk.Button(window, text='Quit', width=10, command=window.destroy).grid(row=7, column=1)
  return window


def main():
  user = getuser()
  root_dir = 'C:/Users/' + user + '/Documents/Xenia/content'
  window = tk.Tk()
  window = init_ui(window, root_dir)
  window.mainloop()


main()
