#!/usr/bin/env python3.5
import argparse
import os
import numpy as np
import pickle
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import scipy.stats as stats
from scipy.interpolate import RegularGridInterpolator
from collections import Counter


"""
This code should be run after parse_volumes_dataset.py
and before easy_experiments_runner.py
It gets the .pkl files generated by parse_volumes_dataset.py
and saves a single .npz file. It may perform some transformation
on the data too, like rotating it to increase the number of samples,
or separate the 3D volumes in 3 channels 2D slices.
"""


np.random.seed(123)  # for reproducibility


def save_plt_figures_to_pdf(filename, figs=None, dpi=200):
    """Save all matplotlib figures in a single PDF file."""
    dirname = os.path.dirname(filename)
    try:
        os.mkdir(dirname)
    except OSError:
        pass
    pp = PdfPages(filename)
    if figs is None:
        figs = [plt.figure(n) for n in plt.get_fignums()]
    for fig in figs:
        fig.savefig(pp, format='pdf')
    pp.close()
    print("PDF file saved in '{}'.".format(filename))


def save_data(x_set, y_set, patients, number, suffix=""):
    """Save information from x_set and y_set. Old method (naive one)."""
    if number == 1 or number == 2:
        # Split volumes in slices_per_sample (3) layers images
        counter = 0
        rotations = 4
        normalize = True
        slices_per_sample = 3
        for volume, label, patient in zip(x_set, y_set, patients):
            # Normalize values from 0 to 1
            maxv = np.max(volume)
            minv = np.min(volume)
            if normalize:
                volume = (volume - minv) / (maxv - minv)
            for r in range(rotations):
                # If rotations=4, rotate img 4 times (0, 90, 180 and 270 deg) to incr. sample size
                vol = np.rot90(volume, k=r)
                for idx in range(vol.shape[2] - slices_per_sample + 1):
                    image = vol[:, :, idx:idx + slices_per_sample]
                    try:
                        x_dataset = np.concatenate((x_dataset, [image]))
                        y_dataset = np.concatenate((y_dataset, [label]))
                        patients_dataset.append(patient)
                    except NameError:
                        x_dataset = np.array([image])
                        y_dataset = np.array([label])
                        patients_dataset = [patient]
            counter += 1
            print("{} / {} patients processed".format(counter, len(patients)))
        print("Processing finished! Saving data...")
        # Save data
        x = x_dataset
        y = y_dataset
        try:
            os.mkdir("data")
        except OSError:
            pass
        full_path = "data/"
        folder_path = full_path + "radiomics{}{}".format(suffix, number)
        file_path = "{}/radiomics{}{}".format(folder_path, suffix, number)
        try:
            os.mkdir(folder_path)
        except OSError:
            pass
        np.savez(file_path, x=x, y=y)
        print("Dataset saved in: '{}.npz'".format(file_path))
        with open("{}_patients.pkl".format(file_path), "wb") as f:
            pickle.dump(patients_dataset, f)
        print("Patients saved in '{}_patients.pkl'.".format(file_path))
    else:
        print("Dataset number '{}' unknown, data was not saved".format(number))


def get_size_mask(mask):
    """Get size box and volume of mask where we can fit all 1s in contour."""
    pixel_shape = mask.shape
    mask_range = [[pixel_shape[0], pixel_shape[1], pixel_shape[2]], [-1, -1, -1]]
    volume = 0
    for xx in range(pixel_shape[0]):
        for yy in range(pixel_shape[1]):
            for zz in range(pixel_shape[2]):
                if mask[xx, yy, zz]:
                    volume += 1
                    mask_range[0][0] = min(mask_range[0][0], xx)
                    mask_range[0][1] = min(mask_range[0][1], yy)
                    mask_range[0][2] = min(mask_range[0][2], zz)
                    mask_range[1][0] = max(mask_range[1][0], xx)
                    mask_range[1][1] = max(mask_range[1][1], yy)
                    mask_range[1][2] = max(mask_range[1][2], zz)
    box_size = np.array(mask_range[1]) - np.array(mask_range[0]) + 1
    return box_size, volume


def plot_histogram(data, title=None, figure=0, subfigure=None, bins=10, xlim=None, show=True,
                   percentages=(0.1, 0.25, 0.75, 0.9), figsize=(8 * 2, 6 * 2), window_title=None,
                   close_all=False):
    """Plot histogram of data."""
    sorted_data = sorted(data)
    # Close and erase all old figures
    if close_all:
        plt.close("all")
    # This is a fitting indeed (draws normal distribution centered at mean)
    fit = stats.norm.pdf(sorted_data, np.mean(sorted_data), np.std(sorted_data))
    fig = plt.figure(figure, figsize=figsize)
    if subfigure is not None:
        fig.add_subplot(subfigure)
    plt.plot(sorted_data, fit, '.-')
    # Use this to draw histogram of the data
    plt.hist(sorted_data, normed=True, bins=bins)
    if xlim is not None:
        plt.xlim(xlim)
    if title is not None:
        plt.title(title)
        fig.canvas.set_window_title("Figure {} - {}".format(figure, title))
    if window_title is not None:
        fig.canvas.set_window_title("Figure {} - {}".format(figure, window_title))
    # Add vertical lines in percentages
    if percentages is not None:
        for i, p in enumerate(percentages):
            pos = int(np.round(len(sorted_data) * p))
            if p == 0.1 or p == 0.9:
                linestyle = "-."
                linecolor = "#904040"
            elif p == 0.25 or p == 0.75:
                linestyle = "--"
                linecolor = "#409040"
            else:
                linestyle = ":"
                linecolor = "#404090"
            label = None
            if p == 0.1:
                label = "10 % - 90 %"
            elif p == 0.25:
                label = "25 % - 75 %"
            plt.axvline(x=sorted_data[pos], linestyle=linestyle, color=linecolor, lw=1,
                        label=label)
        plt.legend()
        # plt.tight_layout()  # Avoids overlap text and figures
    if show:
        plt.show()


def plot_boxplot(data, title=None, figure=0, subfigure=None, ylim=None, hide_axis_labels=False,
                 window_title=None, show=True, close_all=False):
    """Plot a boxplot (figure where we can easily see median, var and mean) of data."""
    # Close and erase all old figures
    if close_all:
        plt.close("all")
    # Draw boxplot
    fig = plt.figure(figure)
    if subfigure is None:
        subfigure = 111
    ax = fig.add_subplot(subfigure)
    ax.boxplot(data, showmeans=True)
    if ylim is not None:
        plt.ylim(ylim)
    if title is not None:
        plt.title(title)
        fig.canvas.set_window_title("Figure {} - {}".format(figure, title))
    if window_title is not None:
        fig.canvas.set_window_title("Figure {} - {}".format(figure, window_title))
    if hide_axis_labels:
        ax.tick_params(labelleft='off')
    ax.tick_params(labelbottom='off')
    if show:
        plt.show()


def trim_edges(array_sort, sort_method, x_set, y_set, patients, masks, trim_pos=(0.1, 0.9)):
    """Remove top and bottom data (data further from average).

    array_sort: array that determines how data is sorted, which determines what stays or is trimmed
    sort_method: 3 possible values: "slices", "sizes" and "sizes_masks"
    """
    arr = np.array(array_sort)
    num_left = int(np.round(len(array_sort) * trim_pos[0]))
    num_right = int(np.round(len(array_sort) * (1 - trim_pos[1] + trim_pos[0])) - num_left)
    val_left = array_sort[arr.argsort()[num_left - 1]]
    val_right = array_sort[arr.argsort()[-num_right]]
    new_x_set = []
    new_y_set = []
    new_patients = []
    new_masks = []
    n_trimmed_pts = 0
    print("\nDISCARDED DATA POINTS BASED ON '{}':".format(sort_method))
    for i, (x, y, p, m) in enumerate(zip(x_set, y_set, patients, masks)):
        slices = len(x[0][0])
        dimensions_mask, size = get_size_mask(m)
        size_box = np.prod(dimensions_mask)
        trim_it = True
        if sort_method == "slices":
            if slices > val_left and slices < val_right:
                trim_it = False
        elif sort_method == "sizes":
            if size > val_left and size < val_right:
                trim_it = False
        elif sort_method == "sizes_masks":
            if size_box > val_left and size_box < val_right:
                trim_it = False
        else:
            print("Error, only parameters accepted: {}".format(["slices", "sizes", "sizes_masks"]))
            return None
        if not trim_it:
            new_x_set.append(x)
            new_y_set.append(y)
            new_patients.append(p)
            new_masks.append(m)
        else:
            n_trimmed_pts += 1
            print("  {}: Index: {}, Slices: {}, Size: {}, Box Size: {}".format(n_trimmed_pts, i,
                                                                               slices, size,
                                                                               size_box))
    print("\nREMAINING DATA DIMENSIONS:")
    print("  Removed data with '{0}' <= {1}, or '{0}' >= {2}".format(sort_method, val_left,
                                                                     val_right))
    print("  Size new dataset: {}".format(len(new_y_set)))
    return new_x_set, new_y_set, new_patients, new_masks


def calculate_shared_axis(data1, data2, constant_factor=0.05):
    """Get shared axis of data1 and data2: [min(data1, data2), max(data1, data2]]."""
    max_val = max(max(data1), max(data2))
    min_val = min(min(data1), min(data2))
    max_val += (max_val - min_val) * constant_factor
    min_val -= (max_val - min_val) * constant_factor
    return (min_val, max_val)


def analyze_data(volumes, labels, patients, masks, plot_data=True, initial_figure=0, suffix="",
                 title_suffix="", dataset_name="organized"):
    """Print statistics of data and maybe plot them if plot_data is True."""
    num_labels = [0, 0]
    sizes_masks = [np.zeros(3), np.zeros(3)]
    all_sizes_masks = [[], []]
    all_sizes = [[], []]
    all_slices = [[], []]
    abs_num_slices = []
    for label, patient, volume, mask in zip(labels, patients, volumes, masks):
        if volume.shape[2] < 3:
            continue  # patient ignored, it is too small
        size_mask, granular_volume = get_size_mask(mask)
        abs_num_slices.append(size_mask[2])
        if abs_num_slices[-1] < 3:
            continue  # patient ignored, it is too small (but we have added it to abs_num_slices)
        all_sizes[label].append(granular_volume)
        sizes_masks[label] += size_mask
        all_sizes_masks[label].append(np.prod(size_mask))
        all_slices[label].append(volume.shape[2])
        num_labels[label] += 1
    sizes_masks_mean = [s/n for s, n in zip(sizes_masks, num_labels)]
    print("\nNumber patients:", num_labels[0] + num_labels[1])
    print(" ")
    print("LABEL 1")
    print("  NUMBER SAMPLES: {}".format(num_labels[1]))
    print("  TUMOR BOX VOLUME (px^3 of tumor box)")
    print("    Mean:     {} (in 3 directions: {})".format(np.prod(sizes_masks_mean[1]),
                                                          sizes_masks_mean[1]))
    print("    Median:   {}".format(np.median(all_sizes_masks[1])))
    print("    Variance: {}".format(np.var(all_sizes_masks[1])))
    print("    Min:      {}".format(np.min(all_sizes_masks[1])))
    print("    Max:      {}".format(np.max(all_sizes_masks[1])))
    print("  NUMBER SLICES")
    print("    Mean:     {}".format(np.mean(all_slices[1])))
    print("    Median:   {}".format(np.median(all_slices[1])))
    print("    Variance: {}".format(np.var(all_slices[1])))
    print("    Min:      {}".format(np.min(all_slices[1])))
    print("    Max:      {}".format(np.max(all_slices[1])))
    print("  GRANULAR VOLUME (px^3 that were labeled as tumor)")
    print("    Mean:     {}".format(np.mean(all_sizes[1])))
    print("    Median:   {}".format(np.median(all_sizes[1])))
    print("    Variance: {}".format(np.var(all_sizes[1])))
    print("    Min:      {}".format(np.min(all_sizes[1])))
    print("    Max:      {}".format(np.max(all_sizes[1])))
    print(" ")
    print("LABEL 0")
    print("  NUMBER SAMPLES: {}".format(num_labels[0]))
    print("  TUMOR BOX VOLUME (px^3 of tumor box)")
    print("    Mean:     {} (in 3 directions: {})".format(np.prod(sizes_masks_mean[0]),
                                                          sizes_masks_mean[0]))
    print("    Median:   {}".format(np.median(all_sizes_masks[0])))
    print("    Variance: {}".format(np.var(all_sizes_masks[0])))
    print("    Min:      {}".format(np.min(all_sizes_masks[0])))
    print("    Max:      {}".format(np.max(all_sizes_masks[0])))
    print("  NUMBER SLICES")
    print("    Mean:     {}".format(np.mean(all_slices[0])))
    print("    Median:   {}".format(np.median(all_slices[0])))
    print("    Variance: {}".format(np.var(all_slices[0])))
    print("    Min:      {}".format(np.min(all_slices[0])))
    print("    Max:      {}".format(np.max(all_slices[0])))
    print("  GRANULAR VOLUME (px^3 that were labeled as tumor)")
    print("    Mean:     {}".format(np.mean(all_sizes[0])))
    print("    Median:   {}".format(np.median(all_sizes[0])))
    print("    Variance: {}".format(np.var(all_sizes[0])))
    print("    Min:      {}".format(np.min(all_sizes[0])))
    print("    Max:      {}".format(np.max(all_sizes[0])))
    print(" ")
    if plot_data:
        plt.ion()
    num_bins = 20
    f = initial_figure
    xlim = calculate_shared_axis(all_slices[0], all_slices[1])
    plot_histogram(all_slices[0], "Slices 0", f, 311, num_bins, xlim, show=plot_data,
                   close_all=True)
    plot_histogram(all_slices[1], "Slices 1", f, 312, num_bins, xlim, show=plot_data)
    plot_histogram(all_slices[0] + all_slices[1], "Slices Total", f, 313, num_bins, xlim,
                   window_title="Slices " + title_suffix, show=plot_data)
    f += 1
    xlim = calculate_shared_axis(all_sizes[0], all_sizes[1])
    plot_histogram(all_sizes[0], "Sizes 0", f, 311, num_bins, xlim, show=plot_data)
    plot_histogram(all_sizes[1], "Sizes 1", f, 312, num_bins, xlim, show=plot_data)
    plot_histogram(all_sizes[0] + all_sizes[1], "Sizes Total", f, 313, num_bins, xlim,
                   window_title="Sizes " + title_suffix, show=plot_data)
    f += 1
    xlim = calculate_shared_axis(all_sizes_masks[0], all_sizes_masks[1])
    plot_histogram(all_sizes_masks[0], "Sizes Box 0", f, 311, num_bins, xlim, show=plot_data)
    plot_histogram(all_sizes_masks[1], "Sizes Box 1", f, 312, num_bins, xlim, show=plot_data)
    plot_histogram(all_sizes_masks[0] + all_sizes_masks[1], "Sizes Box Total", f, 313,
                   num_bins, xlim, window_title="Sizes Box " + title_suffix, show=plot_data)
    f += 1
    ylim = calculate_shared_axis(all_slices[0], all_slices[1])
    plot_boxplot(all_slices[0], "Slices 0", f, 121, ylim, show=plot_data)
    plot_boxplot(all_slices[1], "Slices 1", f, 122, ylim, True, show=plot_data,
                 window_title="Slices " + title_suffix)
    f += 1
    ylim = calculate_shared_axis(all_sizes[0], all_sizes[1])
    plot_boxplot(all_sizes[0], "Sizes 0", f, 121, ylim, show=plot_data)
    plot_boxplot(all_sizes[1], "Sizes 1", f, 122, ylim, True, show=plot_data,
                 window_title="Sizes " + title_suffix)
    f += 1
    ylim = calculate_shared_axis(all_sizes_masks[0], all_sizes_masks[1])
    plot_boxplot(all_sizes_masks[0], "Sizes box 0", f, 121, ylim, show=plot_data)
    plot_boxplot(all_sizes_masks[1], "Sizes box 1", f, 122, ylim, True, show=plot_data,
                 window_title="Sizes Box " + title_suffix)
    # Save PDF results
    save_plt_figures_to_pdf("data/{}/results{}.pdf".format(dataset_name, suffix))
    if plot_data:
        input("Press ENTER to close all figures and continue.")
        plt.close("all")
        plt.ioff()
    return ((num_labels[0], num_labels[1]), (np.median(all_slices[0]), np.median(all_slices[1])),
            (all_slices, all_sizes, all_sizes_masks, abs_num_slices))


def get_bucket(bucket0, bucket1, ratio=0.5):
    """Get size of two buckets and tell what bucket to put next obj to get closer to buckets ratio.

    For example, if buckets=[2, 3] and ratio=0.5, returns 0 to get [3, 3],
    but if ratio=0.66 returns 1 to obtain [2, 4]
    Assumes only 2 buckets, will ignore any other buckets
    Assumes numbers in buckets >= 0
    """
    try:
        current_ratio = bucket0 / (bucket0 + bucket1)
    except ZeroDivisionError:
        current_ratio = 0
    return 0 if current_ratio < ratio else 1


def generate_2D_dataset(samples, labels, patients, masks, slices_per_sample=3, rotate_data=False,
                        normalize=True):
    """From 3D volumes generates a 2D dataset."""
    counter = 0
    rotations = 4 if rotate_data else 1
    for volume, label, patient, mask in zip(samples, labels, patients, masks):
        # Normalize values from 0 to 1
        if normalize:
            maxv = np.max(volume)
            minv = np.min(volume)
            volume = (volume - minv) / (maxv - minv)
        for r in range(rotations):
            # If rotations=4, rotate image 4 times (0, 90, 180 and 270 deg) to increase sample size
            vol = np.rot90(volume, k=r)
            msk = np.rot90(mask, k=r)
            for idx in range(vol.shape[2] - slices_per_sample + 1):
                image = vol[:, :, idx:idx + slices_per_sample]
                mask_image = msk[:, :, idx:idx + slices_per_sample]
                try:
                    x_dataset = np.concatenate((x_dataset, [image]))
                    y_dataset = np.concatenate((y_dataset, [label]))
                    masks_dataset = np.concatenate((masks_dataset, [mask_image]))
                    patients_dataset.append(patient + (str(r * 90) if r != 0 else ""))
                except NameError:
                    x_dataset = np.array([image])
                    y_dataset = np.array([label])
                    masks_dataset = np.array([mask_image])
                    patients_dataset = [patient + (str(r * 90) if r != 0 else "")]
        counter += 1
        print("{} / {} patients processed".format(counter, len(patients)))
    return x_dataset, y_dataset, patients_dataset, masks_dataset


def save_dataset_correctly(x, y, patients, masks, parent_folder="data", dataset_name="organized",
                           dataset_subname="training_set"):
    """Save data in a not naive way, balancing labels and medians in the training and test set."""
    # Create folder data if it does not exist
    full_path = parent_folder + "/"
    try:
        os.mkdir(full_path)
    except OSError:
        pass
    folder_path = full_path + dataset_name + "/"
    try:
        os.mkdir(folder_path)
    except OSError:
        pass
    file_path = "{}{}".format(folder_path, dataset_subname)
    try:
        np.savez(file_path, x=x, y=y)
        print("Dataset saved in: '{}.npz'".format(file_path))
    except ValueError:
        with open("{}.pkl".format(file_path), "wb") as f:
            pickle.dump(x, f)
            pickle.dump(y, f)
        print("Error while saving set as '.npz'. Dataset saved in: '{}.pkl'".format(file_path))
    with open("{}_patients.pkl".format(file_path), "wb") as f:
        pickle.dump(patients, f)
    print("Patients saved in '{}_patients.pkl'.".format(file_path))
    with open("{}_masks.pkl".format(file_path), "wb") as f:
        pickle.dump(masks, f)
    print("Masks saved in '{}_masks.pkl'.".format(file_path))


def improved_save_data(x_set, y_set, patients, masks, dataset_name="organized", suffix="",
                       plot_data=False, trim_data=True, data_interpolation=None,
                       convert_to_2d=True, resampling=None, skip_dialog=False):
    """Save dataset so labels & slices medians are equally distributed in training and test set."""
    # Add suffixes ta dataset name, so it is easy to know how every dataset was generated
    if not convert_to_2d:
        dataset_name += "_3d"
    if trim_data:
        # 2 represents that we are using sizes (2) to trim, not slices (1), or box_sizes (3)
        trim_option = 2
        dataset_name += "_trimmed{}".format(trim_option)
    if data_interpolation is not None:
        dataset_name += "_interpolated"

    # Analyze data and plot some statistics
    num_patients_by_label, medians_by_label, results = analyze_data(x_set, y_set, patients, masks,
                                                                    plot_data=plot_data,
                                                                    dataset_name=dataset_name)
    if trim_data:
        slices, sizes, box_sizes, abs_num_slices = results
        slices = slices[0] + slices[1]
        sizes = sizes[0] + sizes[1]
        box_sizes = box_sizes[0] + box_sizes[1]
        # Trim based on the number of slices
        x_set1, y_set1, patients1, masks1 = trim_edges(slices, "slices", x_set, y_set, patients,
                                                       masks, trim_pos=(0.1, 0.9))
        _, medians_by_label1, results1 = analyze_data(x_set1, y_set1, patients1, masks1,
                                                      plot_data=plot_data, initial_figure=6,
                                                      suffix="_trimmed_slices",
                                                      title_suffix="(Trimmed Slices)",
                                                      dataset_name=dataset_name)
        # Trim based on the tumor volumes (the number of cubic pixels in the mtv contour)
        x_set2, y_set2, patients2, masks2 = trim_edges(sizes, "sizes", x_set, y_set, patients,
                                                       masks, trim_pos=(0.11, 0.89))
        _, medians_by_label2, results2 = analyze_data(x_set2, y_set2, patients2, masks2,
                                                      plot_data=plot_data, initial_figure=12,
                                                      suffix="_trimmed_sizes",
                                                      title_suffix="(Trimmed Sizes)",
                                                      dataset_name=dataset_name)
        # Trim based on the size of the boxs containing the contour
        x_set3, y_set3, patients3, masks3 = trim_edges(box_sizes, "sizes_masks", x_set, y_set,
                                                       patients, masks, trim_pos=(0.11, 0.89))
        _, medians_by_label3, results3 = analyze_data(x_set3, y_set3, patients3, masks3,
                                                      plot_data=plot_data, initial_figure=18,
                                                      suffix="_trimmed_box_sizes",
                                                      title_suffix="(Trimmed Box Sizes)",
                                                      dataset_name=dataset_name)
        # Use trimed data based on trim_option as dataset
        if trim_option == 1:
            x_set, y_set, patients, masks = x_set1, y_set1, patients1, masks1
            medians_by_label, results = medians_by_label1, results1
        elif trim_option == 2:
            x_set, y_set, patients, masks = x_set2, y_set2, patients2, masks2
            medians_by_label, results = medians_by_label2, results2
        elif trim_option == 3:
            x_set, y_set, patients, masks = x_set3, y_set3, patients3, masks3
            medians_by_label, results = medians_by_label3, results3

    if data_interpolation is not None:
        # Adjust slices so that all pixels are the same with, length and height
        pixel_side = min(data_interpolation)
        print("Interpolating. This may take a few minutes...")
        for i in range(len(x_set)):
            print("{}/{}".format(i + 1, len(x_set)))
            min_coord = np.array([0, 0, 0])
            max_coord = np.multiply(np.array(x_set[i]).shape, data_interpolation)
            x = np.arange(min_coord[0], max_coord[0], data_interpolation[0])
            y = np.arange(min_coord[1], max_coord[1], data_interpolation[1])
            z = np.arange(min_coord[2], max_coord[2], data_interpolation[2])
            max_coord = [max(x) + 0.01, max(y) + 0.01, max(z) + 0.01]
            interpolating_func = RegularGridInterpolator((x, y, z), np.array(x_set[i]))
            rangex = np.arange(min_coord[0], max_coord[0], pixel_side)
            rangey = np.arange(min_coord[1], max_coord[1], pixel_side)
            rangez = np.arange(min_coord[2], max_coord[2], pixel_side)
            xlist = np.zeros((len(rangex), len(rangey), len(rangez)))
            for ii, xi in enumerate(rangex):
                for jj, yi in enumerate(rangey):
                    for kk, zi in enumerate(rangez):
                        xlist[ii, jj, kk] = interpolating_func([xi, yi, zi])[0]
            x_set[i] = xlist
        _, medians_by_label4, results4 = analyze_data(x_set, y_set, patients, masks,
                                                      plot_data=plot_data, initial_figure=24,
                                                      suffix="_interpolated_slices",
                                                      title_suffix="(Interpolated Slices)",
                                                      dataset_name=dataset_name)
        medians_by_label, results = medians_by_label4, results4

    if resampling is not None:
        size_box, num_samples = resampling
        if type(size_box) == int:
            size_box = (size_box, size_box, size_box)
        input("results {} {}".format(len(results[1][0]), len(results[1][1])))

    # After analyze_data, if we do not trim it, we see that we have 77 patients
    # Label 1: NUMBER SAMPLES: 20
    #          MEAN TUMOR BOX VOLUME: 3174
    #          MEAN NUMBER SLICES: 17
    #          MEAN GRANULAR VOLUME: 867
    # LABEL 0: NUMBER SAMPLES: 57
    #          MEAN TUMOR BOX VOLUME: 1440
    #          MEAN NUMBER SLICES: 11
    #          MEAN GRANULAR VOLUME: 486
    # Based on this data, we sample the dataset in the best possible way so all kinds of data is
    # represented in the train and test set. We split data in in 4 groups: label 0 / label 1, and
    # above / below median, and put an equal percentage of everything in train and test set

    if not trim_data:
        train_to_total_ratio = 63 / 77  # 77 patients, let's do training+validation = 63, test = 14
    else:
        train_to_total_ratio = 0.1
    train_nums = [[0, 0], [0, 0]]
    test_nums = [[0, 0], [0, 0]]

    test_set_x = []
    train_set_x = []
    test_set_y = []
    train_set_y = []
    test_set_patients = []
    train_set_patients = []
    test_set_masks = []
    train_set_masks = []

    # Distribute data in train and test set
    median_indices = [[], []]
    for i, (label, patient, volume, mask) in enumerate(zip(y_set, patients, x_set, masks)):
        num_slices = volume.shape[2]
        if num_slices < 3:
            continue  # patient ignored, it is too small
        abs_num_slices = results[3][i]  # Counts number slices that have at least 1 contour pixel
        if abs_num_slices < 3:
            continue  # patient ignored, it is too small
        if num_slices < medians_by_label[label]:
            if get_bucket(train_nums[0][label], test_nums[0][label], train_to_total_ratio) == 0:
                train_nums[0][label] += 1
                train_set_x.append(volume)
                train_set_y.append(label)
                train_set_patients.append(patient)
                train_set_masks.append(mask)
            else:
                test_nums[0][label] += 1
                test_set_x.append(volume)
                test_set_y.append(label)
                test_set_patients.append(patient)
                test_set_masks.append(mask)
        elif num_slices > medians_by_label[label]:
            if get_bucket(train_nums[1][label], test_nums[1][label], train_to_total_ratio) == 0:
                train_nums[1][label] += 1
                train_set_x.append(volume)
                train_set_y.append(label)
                train_set_patients.append(patient)
                train_set_masks.append(mask)
            else:
                test_nums[1][label] += 1
                test_set_x.append(volume)
                test_set_y.append(label)
                test_set_patients.append(patient)
                test_set_masks.append(mask)
        else:
            median_indices[label].append(i)
    for label, indices in enumerate(median_indices):
        for index in indices:
            volume = x_set[index]
            patient = patients[index]
            mask = masks[index]
            if get_bucket(train_nums[0][label] + train_nums[1][label],
                          test_nums[0][label] + test_nums[1][label], train_to_total_ratio) == 0:
                train_nums[0][label] += 1
                train_set_x.append(volume)
                train_set_y.append(label)
                train_set_patients.append(patient)
                train_set_masks.append(mask)
            else:
                test_nums[0][label] += 1
                test_set_x.append(volume)
                test_set_y.append(label)
                test_set_patients.append(patient)
                test_set_masks.append(mask)
    ratio = abs(len(train_set_x) / (len(train_set_x) + len(test_set_x)) - train_to_total_ratio)
    ratio0 = abs((len(train_set_x) + 1) /
                 (len(train_set_x) + len(test_set_x)) - train_to_total_ratio)
    ratio1 = abs((len(train_set_x) - 1) /
                 (len(train_set_x) + len(test_set_x)) - train_to_total_ratio)
    if ratio0 < ratio:
        train_set_x.append(test_set_x.pop())
        train_set_y.append(test_set_y.pop())
        train_set_patients.append(test_set_patients.pop())
        train_set_masks.append(test_set_masks.pop())
    elif ratio1 < ratio:
        test_set_x.append(train_set_x.pop())
        test_set_y.append(train_set_y.pop())
        test_set_patients.append(train_set_patients.pop())
        test_set_masks.append(train_set_masks.pop())

    # Print results
    print("\nDATASET DIVIDED IN TRAINING AND TEST SET")
    print("  TRAINING SET")
    print("    Number of samples: {}".format(len(train_set_x)))
    print("    Label frequency: {}".format(dict(Counter(train_set_y))))
    print("  TEST SET")
    print("    Number of samples: {}".format(len(test_set_x)))
    print("    Label frequency: {}\n".format(dict(Counter(test_set_y))))

    # Possibly convert 3D dataset into 2D dataset and save data
    answer = ""
    while not skip_dialog and (len(answer) <= 0 or answer[0].strip().lower() != "y"):
        print("Are you sure you want to save? This may overwrite some files.")
        answer = input("Type 'y' to save data or Ctrl-C to abort.\n>> ")
    print(" ")
    if convert_to_2d:
        train_data = generate_2D_dataset(train_set_x, train_set_y, train_set_patients,
                                         train_set_masks)
        x, y, patients_dataset, masks_dataset = train_data
        print(" ")
    else:
        x, y = train_set_x, train_set_y
        patients_dataset, masks_dataset = train_set_patients, train_set_masks
    save_dataset_correctly(x, y, patients_dataset, masks_dataset,
                           dataset_name=dataset_name, dataset_subname="training_set")
    print(" ")
    if convert_to_2d:
        test_data = generate_2D_dataset(test_set_x, test_set_y, test_set_patients, test_set_masks)
        x, y, patients_dataset, masks_dataset = test_data
        print(" ")
    else:
        x, y = test_set_x, test_set_y
        patients_dataset, masks_dataset = test_set_patients, test_set_masks
    save_dataset_correctly(x, y, patients_dataset, masks_dataset,
                           dataset_name=dataset_name, dataset_subname="test_set")


def parse_arguments(suffix=""):
    """Parse arguments in code."""
    parser = argparse.ArgumentParser(description="This code requires the files "
                                     "'dataset{0}_images.pkl', 'dataset{0}_labels.pkl', "
                                     "'dataset{0}_patients.pkl', and 'dataset{0}_masks.pkl' "
                                     "(which are generated by the program "
                                     "'parse_volumes_dataset.py'). From such files it generates "
                                     "a training_set and a test_set .npz files and other .pkl "
                                     "files that go with them (maps of the patient names and "
                                     "masks), which are saved in the folder './data/organized'."
                                     " It performs some transformation on the data, like "
                                     "rearranging it to make sure the same percentage of 0 and 1 "
                                     "labels are on both the training and test set, and that the "
                                     "same percentage of patients with a number of slices above "
                                     "and below the median for label 0 and 1 are on both the train"
                                     " and test set. It also separates every 3D volumes in 3 "
                                     "channels 2D slices.".format(suffix))
    parser.add_argument('-p', '--plot', default=False, action="store_true",
                        help="show figures before saving them")
    parser.add_argument('-t', '--trim', default=False, action="store_true",
                        help="get rid of outliers: 10%% smaller and larger tumors")
    parser.add_argument('-i', '--interpolate', default=False, action="store_true",
                        help="interpolate volumes so pixels are cubes: the spacing between "
                        "adjacent pixels is the same in all directions")
    parser.add_argument('-r', '--resample', default=False, action="store_true",
                        help="resample volumes to multiple cubes of size 5x5x5 pixels"
                        "adjacent pixels is the same in all directions")
    parser.add_argument('-3d', '--in_3d', default=False, action="store_true",
                        help="save 3d data instead of slicing it in 3 channels 2d images")
    parser.add_argument('-y', '--yes', default=False, action="store_true",
                        help="skip confirmation dialogs, this will overwrite data without asking")
    return parser.parse_args()


if __name__ == "__main__":
    # 0: original volume is unchanged (just put into smaller box)
    # 1: volume is cut exactly by contour
    # 2: volume is cut by contour but adding margin of 3 pixels
    dataset_format = 0
    file_suffix = ""
    name_suffix = ""
    old_format = False
    if dataset_format > 0:
        file_suffix = str(dataset_format)
        if dataset_format == 1:
            name_suffix = "_cut"
        elif dataset_format == 2:
            name_suffix = "_margincut"
        else:
            name_suffix = "_unknown"

    args = parse_arguments(suffix=file_suffix)

    # Load data
    print("Reading 'dataset{}_images.pkl'".format(file_suffix))
    with open('dataset{}_images.pkl'.format(file_suffix), 'rb') as f:
        x = pickle.load(f)
    print("Reading 'dataset{}_labels.pkl'".format(file_suffix))
    with open('dataset{}_labels.pkl'.format(file_suffix), 'rb') as f:
        y = pickle.load(f)
    print("Reading 'dataset{}_patients.pkl'".format(file_suffix))
    with open('dataset{}_patients.pkl'.format(file_suffix), 'rb') as f:
        patients = pickle.load(f)
    if not old_format:
        print("Reading 'dataset{}_masks.pkl'".format(file_suffix))
        with open('dataset{}_masks.pkl'.format(file_suffix), 'rb') as f:
            masks = pickle.load(f)
    # Make sure x and y are the same length
    assert(len(x) == len(y))
    assert(len(x) == len(patients))
    if old_format:
        save_data(x, y, patients, number=1, suffix=name_suffix)
    else:
        data_interpolation = None
        if args.interpolate:
            # This is the distance between pixels in the x, y and z direction in our dicom images
            data_interpolation = (4.07283, 4.07283, 5.0)
        resampling = None
        if args.resample:
            # Resample to cubes of 5x5x5 pixels. We can also resample to non-cubic figures, passing
            # (7,4,3) instead of 5 to create a cube of 7x4x3
            # If the second parameter is None, it will find the smallest volume, count how many
            # cubes can be sampled from it, and generate that many samples for all patients. It
            # will also automatically balance labels 0 and 1. Set None to a number to select the
            # number of samples that will be created, sampling randomly.
            resampling = (5, None)
        improved_save_data(x, y, patients, masks, suffix=name_suffix, plot_data=args.plot,
                           trim_data=args.trim, data_interpolation=data_interpolation,
                           convert_to_2d=not args.in_3d, resampling=resampling,
                           skip_dialog=args.yes)
