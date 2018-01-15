#!/usr/bin/env python3.5

import sys
import os
import yaml


def search_results(folder=None, pause_in_every_result=True):
    """
    From the selected folder (or current folder if folder == None), filter results according to
    result.yaml
    """

    # Navigate to folder and load result.yaml
    if folder is not None:
        os.chdir(folder)
    with open("results.yaml") as f:
        try:
            result = yaml.load(f)
        except yaml.YAMLError as YamlError:
            print("There was an error parsing 'results.yaml'. Plotting aborted.")
            print(YamlError)
            if folder is not None:
                os.chdir("./..")
            return

    # Extract params from result, which will save all possible values for every key in params
    parameters = {}
    for sample_key in result:
        sample = result[sample_key]
        for key in sample["params"]:
            if key not in parameters:
                parameters[key] = set()
            parameters[key].add(sample["params"][key])

    # params_keys will hold all the plotable keys
    params_keys = sorted(parameters.keys())
    params_dict = dict(zip(params_keys, range(len(params_keys))))
    params_values = []

    # Ask the users what variables to filter
    print("Select the search values for every parameter.")
    print("Leave blank (press ENTER) to ignore a parameter.")
    print(" ")
    for key in params_keys:
        if len(parameters[key]) <= 20 and len(parameters[key]) > 1:
            print("Value for {}. Possible values: {}".format(key, sorted(list(parameters[key]))))
            val = input(">> ")
        else:
            val = ""
        params_values.append(val.strip())

    # Print results
    for sample_key in result:
        sample = result[sample_key]
        sample_filtered = False
        for key in sample["params"]:
            val = params_values[params_dict[key]]
            if val == "":
                continue
            if val != str(sample["params"][key]):
                sample_filtered = True
                break
        if not sample_filtered:
            print("Sample {}:".format(sample_key))
            print("---------------------------------------------------")
            for key in sorted(sample["params"]):
                print("  {:>20}: {}".format(key, sample["params"][key]))
            print("---------------------------------------------------")
            for key in sorted(sample["result"]):
                print("  {:>20}: {}".format(key, sample["result"][key]))
            print("---------------------------------------------------")
            if pause_in_every_result:
                input("Press ENTER to see next result")
            print(" ")
    if folder is not None:
        os.chdir("./..")


if __name__ == "__main__":
    folder = None
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    search_results(folder)

    """
    Expects:
        py search_results.py
        py search_results.py folder
    """