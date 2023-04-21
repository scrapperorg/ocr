import sys
import pandas as pd

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


def get_error_lines(text):
    if "DEBUG" in text:
        lines = []
        for line in text.split('\n'):
            if 'error' in line.lower():
                lines.append(line)
        return '\n'.join(lines)
    return text

def performance_stats(jsonlines_file):
    jsonlines_file = 'performance_0.5.0/perf_analysis_0.5.0_.jsonl'
    df = pd.read_json(jsonlines_file, lines=True)
    df_failed = df[df['status'] != 'ok']
    df = df[df['status'] == 'ok']
    print("*** Statistics for successful documents:")
    print(df.describe())

    print('\n\n')
    print("*** Statistics for failed documents:")
    failed_statuses = df_failed['status'].unique()
    print(f"\t Number of unique reasons for failure {len(failed_statuses)}")
    print("\t Most common reasons for failure:")
    print(df_failed.status.apply(get_error_lines).value_counts())
    print(f"\t Number of failed documents: {len(df_failed)}")

    print('\n\n')
    print("*** Time statistics:")
    print(f"\tMaximum processing time: {round(df['processing_time'].max() / 3600, 2)} hours")
    print(f"\tDocument with maximum processing time: {df.iloc[df['processing_time'].argmax()]}")
    seconds_per_page = df['processing_time'] / df['num_pages']
    print(f"\tAverage processing time per page: {round(seconds_per_page.mean(), 2)} seconds")
    K=30
    print(f'\tTop {K} longest processing times:')
    print(df.iloc[df.processing_time.argsort()[::-1]][:K])


    print('\n\n')
    print("*** Quality statistics:")
    print(f"\tMinimum quality doc: {round(df['ocr_quality'].min(), 2)}%")
    print(f"\tDocument with min quality: {df.iloc[df['ocr_quality'].argmin()]}")
    print(f'\tTop {K} longest processing times:')
    df.iloc[df.ocr_quality.argsort()][:K]

    return df, df_failed




if __name__ == "__main__":
    performance_stats(sys.argv[1])
