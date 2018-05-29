from od_util import is_od
# Example usage. Links will be written into data.json

with open("/home/simon/out.txt") as f:

    for line in f:
        print(line[:-1])
        print(is_od(line[:-1]))
