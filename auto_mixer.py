#!/usr/bin/env python

"""
This file includes code to automatically mix together songs. It also includes a graphical portion accompanying
the mixed songs.
"""

__author__ = "Lucas Pauker"

import os
import sys
import math
from multiprocessing import Process

import psutil
import aubio
import eyed3
import numpy as np
import ctcsound
# Supress output upon importing pydub
sys.stdout = open(os.devnull, 'w')
import pygame
sys.stdout = sys.__stdout__
from pydub import AudioSegment
from pydub.playback import play

class color:
    """
    This class is used for specifying colors displayed in the command line prompts.
    Note: this may not work for some shells.
    """
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def get_file_metadata(file_name):
    """
    This method takes a file path of an mp3 file and returns the artist and title in a dictionary if they exist.
    Note: this method will only work for mp3s.
    """
    metadata = {}
    mp3_file = eyed3.load(file_name)
    if mp3_file.tag.artist:
        metadata["artist"] = mp3_file.tag.artist
    if mp3_file.tag.title:
        metadata["title"] = mp3_file.tag.title
    return metadata

def prompt_user_for_song(song_list, dialogue, blacklist=[]):
    """
    This method prompts the user for a song in the song_list, using the passed in dialogue as the prompt. The songs in
    the optional blacklist argument will not be able to be chosen.
    """
    while True:
        song_choice = input(color.BOLD + dialogue + color.END)
        if (song_choice.isdigit() and int(song_choice) > 0 and
                int(song_choice) <= len(song_list) and song_choice not in blacklist):
            break
        print("Invalid input, please try again")
    return song_list[int(song_choice) - 1]

def intro_dialogue(audio_dir, extension="mp3"):
    """
    This method will initiate intro dialogue, prompting users to pick songs and then returning those songs.
    This method searches for songs with the extension passed (default is mp3) in audio_dir then calls the
    prompt_user_for_song method to prompt the user to pick the songs. Two songs are picked by the user and are
    returned as a tuple, i.e. (first_song, second_song)
    """
    songs_in_dir = os.listdir(audio_dir)
    extension_files = sorted([song.lower() for song in songs_in_dir if (song[-len(extension):] == extension)])
    print(color.BOLD + color.YELLOW + "This program will mix two songs together for you!" + color.END)
    print()
    print(color.BOLD + color.GREEN + "Here are the tracks we found:" + color.END)
    for index, song in enumerate(extension_files, 1):
        if extension == "mp3":
            metadata = get_file_metadata(audio_dir + song)
            if "artist" in metadata and "title" in metadata:
                print("  " + str(index) + ". " + color.UNDERLINE + metadata["title"] + color.END +
                        " by " + metadata["artist"])
            else:
                print("  " + str(index) + ". " + song)
        else:
            print("  " + str(index) + ". " + song)
    first_song_choice = prompt_user_for_song(extension_files, "Pick the first track: ")
    second_song_choice = prompt_user_for_song(extension_files, "Pick the second track: ",
            [str(extension_files.index(first_song_choice) + 1)])
    songs = (first_song_choice, second_song_choice)
    return songs

def recipe_dialogue(recipe_dir):
    """
    This method asks the user if they want to use a recipe. If yes, then the user can pick a recipe out of the
    recipe_dir. The recipe filename is returned. Else, an empty string is returned.
    """
    while True:
        response = input(color.BOLD + "Do you want to use a recipe? " + color.END).lower()
        if response.startswith("n"): return ""
        if response.startswith("y"): break
        print("Invalid response, please try again")
    print(color.BOLD + color.GREEN + "Here are the recipes we found:" + color.END)
    recipes_in_dir = sorted(os.listdir(recipe_dir))
    for index, recipe in enumerate(recipes_in_dir, 1):
        print("  " + str(index) + ". " + recipe)
    while True:
        response = input(color.BOLD + "Pick the recipe: " + color.END)
        if response.isdigit() and int(response) > 0 and int(response) - 1 < len(recipes_in_dir):
            return recipes_in_dir[int(response) - 1]
        print("Invalid response, please try again")

def get_bpm(song_file):
    """
    Given a passed in file path to an audio file, this method returns the average (median) beats per minute.
    This method uses the Aubio library, and is very similar to one of the examples
    here: https://github.com/aubio/aubio/tree/master/python/demos
    """
    samplerate, win_s, hop_s = 44100, 1024, 512
    s = aubio.source(song_file, samplerate, hop_s)
    samplerate = s.samplerate
    o = aubio.tempo("specdiff", win_s, hop_s, samplerate)
    beats = []
    total_frames = 0

    while True:
        samples, read = s()
        is_beat = o(samples)
        if is_beat:
            this_beat = o.get_last_s()
            beats.append(this_beat)
        total_frames += read
        if read < hop_s:
            break

    if len(beats) > 1:
        bpms = 60./np.diff(beats)
        median_bpm = np.median(bpms)
    else:
        median_bpm = 0
        print("No beats found")

    return median_bpm

def compile_drum_file(bpm, track_length, file_name, output_file):
    """
    This method takes a bpm, track_length, a file_name for the csd file (csound file) and an output_file. This
    method will compile the input csd file into the audio output_file (wav, for example). The input variables
    will be put in the correct spots according to the following format. {output_file} in the csd will be replaced
    with output_file, {bpm} will be replaced with bpm, and {number_of_beats} will be calculated from the
    track_length in seconds.
    """
    track_minutes = track_length / 60.0
    number_of_beats = int(bpm * track_minutes)
    c = ctcsound.Csound()
    f_in = open(file_name, "r")
    f_out = open("tmp.csd", "w")
    for line in f_in:
        if "{output_file}" in line:
            line = line.replace("{output_file}", output_file)
        if "{bpm}" in line:
            line = line.replace("{bpm}", str(bpm))
        if "{number_of_beats}" in line:
            line = line.replace("{number_of_beats}", str(number_of_beats))
        f_out.write(line)
    f_in.close()
    f_out.close()

    ret = c.compileCsd("tmp.csd")
    if ret == ctcsound.CSOUND_SUCCESS:
        c.start()
        c.perform()
    c.reset()
    # Remove temporary file
    os.remove("tmp.csd")

def normalize_volume(song, target_dBFS=-20.0):
    """
    This method takes a pydub AudioSegment and normalizes it to the target dBFS (decibels relative to the full
    scale). It defaults to a reasonable value of -20.0.
    """
    change_in_dBFS = target_dBFS - song.dBFS
    return song.apply_gain(change_in_dBFS)

def speed_change(song, speed=1.0):
    """
    Given a pydub AudioSegment, this song changes the speed of the song by the factor passed in. This is
    implemented by changing how many samples are played per second.
    """
    song_with_altered_frame_rate = song._spawn(song.raw_data, overrides={
         "frame_rate": int(song.frame_rate * speed)
      })
    return song_with_altered_frame_rate.set_frame_rate(song.frame_rate)

def get_beat(song_file, n=0):
    """
    This method returns the number of milliseconds until the nth beat in the passed in audio file. This method
    is extremely useful for aligning songs.
    """
    samplerate, win_s, hop_s = 44100, 1024, 512
    s = aubio.source(song_file, samplerate, hop_s)
    samplerate = s.samplerate
    o = aubio.tempo("specdiff", win_s, hop_s, samplerate)
    beat_count = 0
    time_count = 0

    while True:
        samples, read = s()
        is_beat = o(samples)
        if is_beat:
            this_beat = o.get_last_ms()
            beat_count += 1
            time_count += this_beat
            if beat_count >= n: return this_beat
        if read < hop_s:
            break
    return 0

def align_song(song, time, correction):
    """
    Given a pydub AudioSegment and a file_name for an audio file, this method will return an AudioSegment with
    all the material up to the first beat cut out. This method is made explicit for clarity.
    """
    if correction < 0:
        return song[:time - correction] + song[time:]
    else:
        return song[:time] + AudioSegment.silent(duration=correction) + song[time:]

def apply_repeat(song, args, bpm):
    """
    This method applies the repeat effect to the song passed in. This method utilizes the inputted bpm to make sure
    that the song stays on beat. The song with the effect is returned.
    """
    seconds_per_beat = 60.0 / bpm
    position = float(args[2]) * 1000
    displacement = (float(args[0]) - float(args[0]) % seconds_per_beat) * 1000
    audio_splice = song[position : position + displacement] * int(args[1])
    return song[:position] + audio_splice + song[position + displacement:]

def apply_fade(song, args):
    """
    This method applies the fade effect to the song passed in. The song with the effect is returned.
    """
    dB_change = 10.0
    if len(args) > 3:
        dB_change = float(args[3])
    if args[1] == "IN":
        gain = dB_change
    else:
        gain = -1 * dB_change
    return song.fade(to_gain=gain, start=int(args[2]) * 1000, duration=int(args[0]) * 1000)

def apply_speed(song, args, bpm):
    """
    This method applies the speed up/slow down effect to the song passed in. This method utilizes the inputted bpm
    to make sure that the song stays on beat. The song with the effect is returned.
    """
    position = float(args[2]) * 1000
    if len(args) > 3:
        speed_factor = float(args[3])
    elif args[1] == "FAST":
        speed_factor = 1.5
    else:
        speed_factor = 1 / 1.5
    sped_up_bpm = bpm / speed_factor
    seconds_per_beat = 60.0 / sped_up_bpm
    displacement = ((float(args[0]) * speed_factor) - (float(args[0]) * speed_factor) % seconds_per_beat) * 1000
    audio_splice = speed_change(song[position : position + displacement], speed_factor)
    return song[:position] + audio_splice + song[position + displacement:]

def apply_recipe(first_song, second_song, recipe_file, bpm):
    """
    This method applies the recipe to the two songs passed in. The rules for the recipe are specified in the
    simple_recipe.dj file. A brief overview: this method parses the file and looks for lines starting with
    a valid command and executes the command on the songs. Valid commands include "fade", "repeat", "speed",
    and "slice"
    """
    valid_commands = ["fade", "repeat", "speed", "slice"]
    recipe = open(recipe_file, "r")
    for line in recipe:
        if str.strip(line) and not line.startswith("#"):
            split_line = line.split()
            command = split_line[0].lower()
            if command not in valid_commands:
                print("Syntax Error: " + split_line[0] + " is not a valid command")
                continue
            elif split_line[1] not in ["s1", "s2"]:
                print("Syntax Error: " + split_line[1] + " is not a valid object")
                continue
            if split_line[1] == "s1":
                obj = first_song
            else:
                obj = second_song
            if command == "repeat":
                if split_line[1] == "s1": first_song = apply_repeat(first_song, split_line[2:], bpm)
                else: second_song = apply_repeat(second_song, split_line[2:], bpm)
            elif command == "fade":
                if split_line[1] == "s1": first_song = apply_fade(first_song, split_line[2:])
                else: second_song = apply_fade(second_song, split_line[2:])
            elif command == "speed":
                if split_line[1] == "s1": first_song = apply_speed(first_song, split_line[2:], bpm)
                else: second_song = apply_speed(second_song, split_line[2:], bpm)
            elif command == "slice":
                first_song = first_song[:1000 * int(split_line[2])]
    recipe.close()
    return first_song.overlay(second_song)

def mix_songs(first_song_file, second_song_file, drum_file, song_length, recipe_file=""):
    """
    Given two song audio files as mp3s and a drum audio file as a wav file, this method mixes the songs together
    and returns a pydub AudioSegment of the remix. The optional argument song_length allows the user to choose to
    only have the first song_length seconds of the song. When song_length=0, the entire length of the remix
    is returned.
    """
    first_song = normalize_volume(AudioSegment.from_mp3(first_song_file))
    second_song = normalize_volume(AudioSegment.from_mp3(second_song_file))
    drum_track = normalize_volume(AudioSegment.from_wav(drum_file))

    if song_length != 0:
        first_song = first_song[:song_length * 1000]

    first_bpm = get_bpm(first_song_file)
    second_bpm = get_bpm(second_song_file)
    bpm_shift = first_bpm / second_bpm
    second_song = speed_change(second_song, bpm_shift)
    second_song.export("tmp.flac", format="flac")

    track_minutes = first_song.duration_seconds / 60.0
    number_of_beats = int(first_bpm * track_minutes)
    beat_number = 0
    drum_offset = 0
    second_offset = 0
    beat_interval = 5
    while beat_number < number_of_beats:
        beat_time = get_beat(first_song_file, beat_number)
        second_beat_time = get_beat("tmp.flac", beat_number)
        drum_beat_time = beat_number * (60.0 / first_bpm) * 1000
        second_correction = second_beat_time - drum_beat_time - second_offset
        drum_correction = drum_beat_time - beat_time - drum_offset
        second_song = align_song(second_song, second_beat_time, second_correction)
        drum_track = align_song(drum_track, drum_beat_time, drum_correction)
        second_offset += second_correction
        drum_offset += drum_correction
        beat_number += beat_interval
    os.remove("tmp.flac")

    if recipe_file:
        mixed_song = apply_recipe(first_song, second_song, recipe_file, first_bpm)
    else:
        mixed_song = first_song.overlay(second_song)

    overlay = mixed_song.overlay(drum_track)
    return overlay

def get_beats(song):
    """
    This method takes a pydub AudioSegment and returns a list of the times where each beat in the song occurs.
    It does this by iterating through all the beats and utilizing the get_beat method.
    """
    song.export("tmp.flac", format="flac")
    bpm = get_bpm("tmp.flac")
    track_minutes = song.duration_seconds / 60.0
    number_of_beats = int(bpm * track_minutes)
    beat_number = 1
    beats = []
    while beat_number < number_of_beats:
        beats.append(get_beat("tmp.flac", beat_number))
        beat_number += 1
    os.remove("tmp.flac")
    return beats

def run_animation(beats, thread):
    """
    This method uses pygame to create an animation that goes along with the beat. It takes a bpm and a thread as
    inputs. The bpm is used so that the animation pulsates with the beat, and the thread is needed so that when
    the animation is exited, the thread is also killed. The purpose of this is that playing the song should be run
    in a separate thread.
    """
    pygame.init()
    pygame.display.set_caption("auto_mixer")
    clock = pygame.time.Clock()
    clock.tick()
    size = width, height = 500, 500
    screen = pygame.display.set_mode(size)
    radius = min(width, height) / 2 - 50
    theta = 0
    length = 1
    length_change = 0
    arm_width = 10
    max_num_angles = 16
    num_angles = max_num_angles
    color_offset = 0
    asc = False
    beat_counter = 0
    while True:
        # Handle exiting the app, and send SIGTERM to the thread and its children
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                parent = psutil.Process(thread.pid)
                children = parent.children(recursive=True)
                for child in children:
                    child.kill()
                sys.exit()

        clock.tick()
        beat_diff = beats[beat_counter] if beat_counter == 0 else beats[beat_counter] - beats[beat_counter - 1]
        length_change = (clock.get_time() * 2) / beat_diff

        BACKGROUND_COLOR = (100 + color_offset / 2, 255 - color_offset / 2, 255 - color_offset / 2)
        ARM_COLOR = (color_offset / 2, color_offset / 2, color_offset / 2)
        OUTER_CIRCLE_COLOR = (0, 0, 255 - color_offset)
        INNER_CIRCLE_COLOR = (color_offset, 0, 0)

        screen.fill(BACKGROUND_COLOR)
        angles = []
        for i in range(num_angles):
            angles.append((2 * math.pi) * i / num_angles)
        for angle in angles:
            x_pos = radius * math.cos(theta + angle)
            y_pos = radius * math.sin(theta + angle)
            pygame.draw.line(screen, ARM_COLOR, [int(width / 2), int(height / 2)],
                    [width / 2 + length * x_pos, height / 2 + length * y_pos], arm_width)
            pygame.draw.circle(screen, ARM_COLOR,
                    [int(width / 2 + length * x_pos), int(height / 2 + length * y_pos)], int(arm_width / 2))
        pygame.draw.circle(screen, OUTER_CIRCLE_COLOR, [int(width / 2), int(height / 2)], int(15 + length * 30))
        pygame.draw.circle(screen, INNER_CIRCLE_COLOR, [int(width / 2), int(height / 2)], int(10 + length * 20))
        if asc:
            color_offset = min(255, color_offset + length_change * 255)
            length += length_change
            if length >= 1:
                asc = False
        else:
            color_offset = max(0, color_offset - length_change * 255)
            length -= length_change
            if length <= 0:
                if num_angles > 1:
                    num_angles -= 1
                else:
                    num_angles = max_num_angles
                beat_counter += 1
                asc = True
        theta += 0.1
        pygame.display.flip()

if __name__ == "__main__":
    audio_dir = os.getcwd() + "/music/"
    recipe_dir = os.getcwd() + "/recipes/"
    drum_file = "drum_file.csd"
    output_file = "out.wav"
    song_length = 60

    songs = intro_dialogue(audio_dir)
    print()
    recipe_output = recipe_dialogue(recipe_dir)
    recipe_file = recipe_output if not recipe_output else recipe_dir + recipe_output
    first_song_file = audio_dir + songs[0]
    second_song_file = audio_dir + songs[1]
    track_length = AudioSegment.from_mp3(first_song_file).duration_seconds

    bpm = get_bpm(first_song_file)
    compile_drum_file(bpm, track_length, drum_file, output_file)
    mixed_song = mix_songs(first_song_file, second_song_file, output_file, song_length, recipe_file)
    os.remove(output_file)
    beats = get_beats(mixed_song)
    thread = Process(target=play, args=(mixed_song,))
    thread.start()
    run_animation(beats, thread)
