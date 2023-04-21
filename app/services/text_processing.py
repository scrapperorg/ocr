import re
import unicodedata

import numpy as np
from tqdm import tqdm


def remove_diacritics(token):
    return (
        unicodedata.normalize("NFKD", token).encode("ascii", "ignore").decode("ascii")
    )


class Cleaner:
    """Class strongly inspired by the work Stefan Dumitrescu https://github.com/dumitrescustefan/"""

    """
    S- ar putea să fie necesar să- l recitiţi.
    """
    r1 = re.compile(r"([\w]+-)[\s]([\w]+)", re.IGNORECASE)

    """
    {LL/ AAAA}
    Humalog Mix50 100 U/ ml
    """
    r2 = re.compile(r"([\w]+/)\s([\w]+)", re.IGNORECASE)

    """
    All unicode dashes to normal '-', see https://www.fileformat.info/info/unicode/category/Pd/list.htm
    includes bull : • \u2022
    """
    r3 = re.compile(
        r"([■\u2022\u007E\u00AD\u058A\u05BE\u1400\u1806\u2010\u2011\u2012\u2013\u2014\u2015\u2053\u207B\u208B\u2212\u2E17\u2E3A\u2E3B\u301C\u3030\u30A0\uFE31\uFE32\uFE63\uFF0D]+)",
        re.UNICODE,
    )

    """
    spaces after comma in numbers: 1, 4% -> 1,4%
    """
    r4 = re.compile(r"([\d]+,)\s([\d]+)", re.IGNORECASE)

    """
    soft hyphens #\u00AD
    """
    r5 = re.compile(r"[\u00AD]")

    """
    remove URLS
    """
    r6 = re.compile(r"(?:www|http)\S+|<\S+|\w+\/*>")

    """
    remove emails
    """
    r7 = re.compile(r"([^@]+@[^@]+\.[^@]+)")

    """
    table separators
    """
    r8 = re.compile(r"[\─\─]+")
    r9 = re.compile(r"[\-\-]+")

    """
    multiple spaces
    """
    space = re.compile(" +")

    """
    forbiden chars that cause a lot of bad sentences
    """
    forbidden_chars = "ºþÈ™ÓÑÄÈÃ®ƒ"

    def clean(
        self,
        lines,
        percent_max_numeric=0.7,
        percent_max_non_ascii=0.40,
        min_line_length=20,
        verbose=False,
        disable_pbar=True,
    ):
        skipped_because_min_length = np.array([0, 0], dtype=np.uint64)
        skipped_alpha_count = np.array([0, 0], dtype=np.uint64)
        skipped_because_max_numeric = np.array([0, 0], dtype=np.uint64)
        skipped_because_max_non_ascii = np.array([0, 0], dtype=np.uint64)
        skipped_because_forbidden_chars = np.array([0, 0], dtype=np.uint64)
        total_original_length = 0
        total_clean_length = 0
        output = []
        for line in tqdm(lines, disable=disable_pbar):
            line = line.strip()

            # get stats about line
            length = len(line)
            total_original_length += length

            if length < min_line_length:
                skipped_because_min_length += np.array([1, length], dtype=np.uint64)
                continue

            line = bytes(line, "utf-8").decode(
                "utf-8", "ignore"
            )  # strip not utf-8 chars

            digit_count = 0
            alpha_count = 0
            ascii_count = 0
            forbidden_char = False
            for char in line:
                if char in self.forbidden_chars:
                    forbidden_char = True
                    break
                if char.isnumeric():
                    digit_count += 1
                if char.isalpha():
                    alpha_count += 1
                if char.isascii():
                    ascii_count += 1

            # reject if forbidden char
            if forbidden_char:
                skipped_because_forbidden_chars += np.array(
                    [1, length], dtype=np.uint64
                )
                continue

            # reject if number of letters is too small
            if alpha_count == 0 or alpha_count / length < 0.5:
                skipped_alpha_count += np.array([1, length], dtype=np.uint64)
                if verbose:
                    print(f"Skipping alpha={alpha_count / length:.3f}: [{line}]")
                continue

            # reject if too many numbers
            if digit_count / alpha_count >= percent_max_numeric and digit_count > 6:
                skipped_because_max_numeric += np.array([1, length], dtype=np.uint64)
                if verbose:
                    print(
                        "Skipping digit={:.3f}: [{}]".format(
                            digit_count / alpha_count, line
                        )
                    )
                continue
            # reject if too many non-ascii
            if ascii_count / alpha_count < percent_max_non_ascii and length > 15:
                skipped_because_max_non_ascii += np.array([1, length], dtype=np.uint64)
                if verbose:
                    print(
                        "Skipping ascii={:.3f}: [{}]".format(
                            digit_count / alpha_count, line
                        )
                    )
                continue

            # skip lines that appear to be ascii tables │
            if (line.strip()[0] == "|" and line.count("|") > 2) or (
                line.strip()[0] == "│" and line.count("│") > 2
            ):
                skipped_because_forbidden_chars += np.array(
                    [1, length], dtype=np.uint64
                )
                if verbose:
                    print(f"Skipping table line: [{line}]")
                continue

            # clean line
            # print("\nbef: {}".format(line))
            line = self.r1.sub(r"\1\2", line)
            line = self.r2.sub(r"\1\2", line)
            line = self.r3.sub("-", line)
            line = self.r4.sub(r"\1\2", line)
            line = self.r5.sub("", line)
            line = self.r6.sub("", line)
            line = self.r7.sub("", line)
            # separators
            line = self.r8.sub("", line)
            line = self.r9.sub("", line)

            line = line.replace("( ă)", "(ă)")
            line = line.replace("ţ", "ț")
            line = line.replace("ş", "ș")
            line = line.replace("Ţ", "Ț")
            line = line.replace("Ş", "Ș")
            line = line.replace("Ã¢", "â")

            # print("aft: {}".format(line))

            line = self.space.sub(" ", line).strip()

            # check that after processing the line is not too short
            if len(line) < min_line_length:
                skipped_because_min_length += np.array([1, length], dtype=np.uint64)
                continue

            total_clean_length += len(line)
            output.append(line + "\n")

        # pack stats
        stats = {}
        stats["skipped_because_min_length"] = skipped_because_min_length
        stats["skipped_alpha_count"] = skipped_alpha_count
        stats["skipped_because_max_numeric"] = skipped_because_max_numeric
        stats["skipped_because_max_non_ascii"] = skipped_because_max_non_ascii
        stats["skipped_because_forbidden_chars"] = skipped_because_forbidden_chars
        stats["total_original_length"] = total_original_length
        stats["total_clean_length"] = total_clean_length

        return output, stats

    def add_stats(self, a, b):
        """
        Add two stats dict that are returned by the process function.
        This is used for multiple files
        :param a: stats dict
        :param b: stats dict
        :return: stats dict
        """
        stats = {}
        stats["skipped_because_min_length"] = (
            a["skipped_because_min_length"] + b["skipped_because_min_length"]
        )
        stats["skipped_alpha_count"] = (
            a["skipped_alpha_count"] + b["skipped_alpha_count"]
        )
        stats["skipped_because_max_numeric"] = (
            a["skipped_because_max_numeric"] + b["skipped_because_max_numeric"]
        )
        stats["skipped_because_max_non_ascii"] = (
            a["skipped_because_max_non_ascii"] + b["skipped_because_max_non_ascii"]
        )
        stats["skipped_because_forbidden_chars"] = (
            a["skipped_because_forbidden_chars"] + b["skipped_because_forbidden_chars"]
        )
        stats["total_original_length"] = (
            a["total_original_length"] + b["total_original_length"]
        )
        stats["total_clean_length"] = a["total_clean_length"] + b["total_clean_length"]
        return stats

    def print_stats(self, stats):
        print("\nCleaning statistics:")
        print(
            "Total original length (chars) = {}".format(stats["total_original_length"])
        )
        print(
            "Total length after cleaning (chars) = {}".format(
                stats["total_clean_length"]
            )
        )
        print(
            "Percent data kept = {:.3f} %".format(
                100.0 * stats["total_clean_length"] / stats["total_original_length"]
            )
        )

        print(
            "Skipped because line length was below minimum (lines/chars): {} ".format(
                stats["skipped_because_min_length"]
            )
        )
        print(
            "Skipped because line had forbidden characters (lines/chars): {} ".format(
                stats["skipped_because_forbidden_chars"]
            )
        )
        print(
            "Skipped because alpha count was below minimum (lines/chars): {} ".format(
                stats["skipped_alpha_count"]
            )
        )
        print(
            "Skipped because digit count was above maximum (lines/chars): {} ".format(
                stats["skipped_because_max_numeric"]
            )
        )
        print(
            "Skipped because too many non-ascii characters (lines/chars): {} ".format(
                stats["skipped_because_max_non_ascii"]
            )
        )
