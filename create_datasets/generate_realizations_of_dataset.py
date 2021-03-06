#!/usr/bin/env python3.5
import argparse
import matplotlib_handle_display  # Must be imported before anything matplotlib related
import numpy as np
import pickle
from datetime import datetime
from lumpy_model import get_params_label_0, generate_mask, get_lumpy_image
from matplotlib import pyplot as plt
from skimage import feature
from scipy.ndimage.morphology import binary_erosion
import os


def get_current_time(time=True, date=False, microseconds=False):
    """Return string with current time and date well formatted."""
    now = datetime.now()
    s = ""
    if date:
        s += "{} ".format(now.date())
    if time:
        s += "{:02d}:{:02d}:{:02d}".format(now.hour, now.minute, now.second)
    if microseconds:
        if time:
            s += "."
        s += "{:06d}".format(now.microsecond)
    return s.strip()


def remove_healthy_top_and_bottom_slices(image, mask, margin):
    """Remove top and bottom slices that have all 0s masks, minus margin slices."""
    ones_pos = np.nonzero(mask)
    min_z = max(0, np.min(ones_pos[2]) - margin)
    max_z = min(image.shape[2], np.max(ones_pos[2]) + margin + 1)
    return image[:, :, min_z:max_z], mask[:, :, min_z:max_z]


def get_glcm_statistics(volume):
    """Get statistics realted to GLCM."""
    image_medians = [0, 0, 0]
    image_medians[0] = volume[int(volume.shape[0] / 2), :, :]
    image_medians[1] = volume[:, int(volume.shape[1] / 2), :]
    image_medians[2] = volume[:, :, int(volume.shape[2] / 2)]
    all_d = []
    all_c = []
    all_a = []
    for i in range(3):
        image_array = image_medians[i]
        offsets = np.array([1]).astype(np.int)
        radians = np.pi * np.arange(4) / 4
        LEVELS = 16
        lo, hi = image_array.min(), image_array.max()
        image_array = np.round((image_array - lo) / (hi - lo) * (LEVELS - 1)).astype(np.uint8)
        glcms = feature.greycomatrix(image_array, offsets, radians, LEVELS, symmetric=True,
                                     normed=True)
        dissimil = feature.greycoprops(glcms, prop='dissimilarity')
        dissimil = [dissimil[0, angle] for angle in range(radians.size)]
        all_d.append(np.mean(dissimil))
        correlation = feature.greycoprops(glcms, prop='correlation')
        correlation = [correlation[0, angle] for angle in range(radians.size)]
        all_c.append(np.mean(correlation))
        asm = feature.greycoprops(glcms, prop='ASM')
        asm = [asm[0, angle] for angle in range(radians.size)]
        all_a.append(np.mean(asm))
    return np.mean(all_d), np.mean(all_c), np.mean(all_a)


def get_statistics_mask(mask):
    """Get size box and volume of mask where we can fit all 1s in contour."""
    ones_pos = np.nonzero(mask)
    eroded = binary_erosion(mask)
    outer_mask = mask - eroded
    volume = len(ones_pos[0])
    surface = outer_mask.sum()
    return surface, volume, ones_pos


def save_statistics(image, mask, folder=None, dataset_name=None, factor=None):
    """Docstring for save_statistics."""
    if factor is not None:
        image = image * 255
    std_dev = np.std(image)
    mean = np.mean(image)
    median = np.median(image)
    surface, volume, mask_positions = get_statistics_mask(mask)
    surf_to_vol = surface / volume
    dissimilarity, correlation, asm = get_glcm_statistics(image)
    names = ("mean, median, stddev, surface, volume, surf_vol_ratio, dissimilarity, correlation, "
             "asm")
    num_data = [mean, median, std_dev, surface, volume, surf_to_vol, dissimilarity, correlation,
                asm]
    data = [str(mean), str(median), str(std_dev), str(surface), str(volume), str(surf_to_vol),
            str(dissimilarity), str(correlation), str(asm)]
    if folder is not None and dataset_name is not None:
        path = "{}{}_statistics.csv".format(folder, dataset_name)
        if not os.path.exists(path):
            with open(path, "a+") as f:
                f.write(names + "\n")
        with open(path, "a+") as f:
            f.write(", ".join(data) + "\n")
    return num_data, names


def generate_data(c, r, dataset_name="lumpy_dataset", folder="", show_images=False,
                  pause_images=False, discrete_centers=False, lumps_version=0, num_samples=100,
                  number_first_patient=0, cut_edges_margin=None):
    """Generate num_samples lumpy images for label 0 and 1, save them, and possibly plot them."""
    print("Samples generated for each label: " + str(num_samples))

    # Save or show data
    percent = 5
    split_distance = num_samples * percent // 100
    split_distance = 1 if split_distance < 1 else split_distance
    params0 = get_params_label_0(version=lumps_version, discrete_positions=discrete_centers, c=c,
                                 r=r)
    volumes = []
    labels = []
    patients = []
    masks = []
    patient_counter = number_first_patient
    print("{}. 0% loaded (0/{} samples)".format(get_current_time(), num_samples))
    all_stats = []
    for i in range(num_samples):
        # Save lumpy images for label 0 and 1
        image0, lumps, background, pos_lumps0 = get_lumpy_image(*params0)
        mask0 = generate_mask(image0, params0[-1])
        if cut_edges_margin is not None:
            image0, mask0 = remove_healthy_top_and_bottom_slices(image0, mask0, cut_edges_margin)
        volumes.append(image0)
        masks.append(mask0)
        labels.append(0)
        patients.append("{:08d}".format(patient_counter))
        patient_counter += 1

        stats, name_stats = save_statistics(image0, mask0, folder, dataset_name)
        all_stats.append(stats)

        # Create and show plots
        if show_images:
            num0 = image0.shape[2]
            middle0 = int(num0 / 2)
            fig = plt.figure(0)
            ax = fig.add_subplot(1, 2, 1)
            ax.imshow(image0[:, :, middle0])
            ax.set_yticks([])
            ax.set_xticks([])
            ax.set_title("Label 0 - Slice {}/{}".format(middle0, num0))
            ax = fig.add_subplot(1, 2, 2)
            ax.imshow(masks[-2][:, :, middle0])
            ax.set_yticks([])
            ax.set_xticks([])
            ax.set_title("Label 0 - Mask Slice {}/{}".format(middle0, num0))
            # If pause images is not set, we will see the images briefly one after another
            if pause_images:
                s = input("Press ENTER to see the next image, or Q (q) to disable pause:  ")
                if len(s) > 0 and s[0].lower() == "q":
                    pause_images = False

        if (i + 1) % split_distance == 0:
            print("{}. {}% loaded ({}/{} samples)".format(get_current_time(),
                                                          (i + 1) * 100 // num_samples,
                                                          i + 1, num_samples))

    if show_images:
        plt.ioff()

    print(" ")
    print("Saving data, this may take a few minutes")
    # Save the volumes
    with open('{}{}_images.pkl'.format(folder, dataset_name), 'wb') as f:
        pickle.dump(volumes, f)
    print("Data saved in '{}{}_images.pkl'.".format(folder, dataset_name))

    with open('{}{}_labels.pkl'.format(folder, dataset_name), 'wb') as f:
        pickle.dump(labels, f)
    print("Data saved in '{}{}_labels.pkl'.".format(folder, dataset_name))

    with open('{}{}_patients.pkl'.format(folder, dataset_name), 'wb') as f:
        pickle.dump(patients, f)
    print("Data saved in '{}{}_patients.pkl'.".format(folder, dataset_name))

    with open('{}{}_masks.pkl'.format(folder, dataset_name), 'wb') as f:
        pickle.dump(masks, f)
    print("Data saved in '{}{}_masks.pkl'.".format(folder, dataset_name))

    stats = np.array(all_stats)
    means = np.mean(stats, axis=0)
    medians = np.median(stats, axis=0)
    stddevs = np.std(stats, axis=0)
    path = "{}statistics.csv".format(folder)
    if not os.path.exists(path):
        name_stats = name_stats.split(", ")
        all_name_stats = ["mean_{}".format(x) for x in name_stats]
        all_name_stats += ["median_{}".format(x) for x in name_stats]
        all_name_stats += ["stddev_{}".format(x) for x in name_stats]
        all_name_stats += ["c", "r", "n"]
        with open(path, "a+") as f:
            f.write(", ".join(all_name_stats) + "\n")
    with open(path, "a+") as f:
        params = list(means) + list(medians) + list(stddevs)
        f.write(", ".join(str(p) for p in params) + ", {}, {}, {}\n".format(c, r, num_samples))


def parse_arguments():
    """Parse arguments in code."""
    parser = argparse.ArgumentParser(description="Create multiple datasets made of lumpy images"
                                     " with different parameters")
    parser.add_argument('-dc', '--delete_csv', default=False, action="store_true")
    parser.add_argument('-p', '--plot', default=False, action="store_true", help="plot images")
    parser.add_argument('--cmin', default=50, type=int, help="default: 50")
    parser.add_argument('--cmax', default=1000, type=int, help="default: 1000")
    parser.add_argument('--cstep', default=50, type=int, help="default: 50")
    parser.add_argument('--rmin', default=1, type=float, help="default: 1")
    parser.add_argument('--rmax', default=3, type=float, help="default: 3")
    parser.add_argument('--rstep', default=0.25, type=float, help="default: 0.25")
    parser.add_argument('-np', '--num_patients', default=256, type=int, help="default: 256",
                        metavar="N")
    parser.add_argument('-f', '--folder', default="artificial_images/", type=str, metavar="S",
                        help="default: 'artificial_images/'")
    return parser.parse_args()


if __name__ == "__main__":
    c_min = 50
    c_max = 1000
    c_step = 50
    r_min = 1
    r_max = 3
    r_step = 0.25
    n = 256
    folder = "artificial_images/"
    args = parse_arguments()
    c_min = args.cmin
    c_max = args.cmax
    c_step = args.cstep
    r_min = args.rmin
    r_max = args.rmax
    r_step = args.rstep
    n = args.num_patients
    folder = args.folder
    if not folder.endswith("/"):
        folder += "/"
    try:
        os.mkdir(folder)
    except FileExistsError:
        if args.delete_csv:
            # Folder exists
            for f in os.listdir(folder):
                file_path = os.path.join(folder, f)
                try:
                    if file_path.endswith(".csv"):
                        os.unlink(file_path)
                except Exception as e:
                    print(e)
    num_comb = int((c_max - c_min) / c_step) * int((r_max - r_min) / r_step)
    print("Number of combinations: {}".format(num_comb))
    i = 0
    for c in np.arange(c_min, c_max, c_step):
        for r in np.arange(r_min, r_max, r_step):
            i += 1
            print("{}/{}. Centers: {}, Radius(stddev): {}".format(i, num_comb, c, r))
            name = "lumpy_model_c{:04d}_r{:.2f}_n{:04d}".format(c, r, n)
            generate_data(c=c, r=r, num_samples=n, dataset_name=name, folder=folder,
                          show_images=False, pause_images=False,
                          discrete_centers=False, lumps_version=0,
                          number_first_patient=0, cut_edges_margin=None)
