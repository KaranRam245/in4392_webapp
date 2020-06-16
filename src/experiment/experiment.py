import json
import tarfile
import matplotlib.pyplot as plt


class Parser:

    @staticmethod
    def _read_file(filename) -> list:
        """
        Read the given file.
        :param filename:
        :return:
        """
        content = []
        with tarfile.open(filename, 'r', encoding='utf-8') as tar:
            for member in tar.getmembers():
                file = tar.extractfile(member)
                content += file.readlines()
                print(type(content[0]))
        return content

    def parse(self, filename):
        """
        Read a file, convert the lines to metrics, group the metrics and correct the times.
        :param filename: File to extract.
        :return: Metrics with corrected times.
        """
        content = self._read_file(filename)
        with open('test.txt', 'w') as f:
            f.writelines(content)
        metric_lines = self._extract_metrics(content)
        grouped_metrics = self.group_metrics(metric_lines)
        corrected_times = self.correct_time(grouped_metrics)
        return corrected_times

    @staticmethod
    def _extract_metrics(content: list):
        """
        Extract all lines with METRIC
        :param content: List of lines to extract from.
        :return: List of lines with only METRICs.
        """
        metrics = []
        for line in content:
            if not line.startswith('INFO'):  # If not starts with INFO, it is not a metric.
                continue
            line = line.rstrip()  # Remove enter at the end.
            metric_split = line.split('METRIC')
            if len(metric_split) == 1:
                continue
            line = metric_split[1]
            line = json.loads(line)
            metrics.append(line)
        return metrics

    @staticmethod
    def group_metrics(metric_lines):
        """
        Group the metrics on their metric key.
        :param metric_lines: Extracted metric lines (see _extract_metrics).
        :return: Grouped metrics on metric key.
        """
        grouped_metrics = {}
        for metric_line in metric_lines:
            for key, value in metric_line.items():
                if key != 'time':
                    grouped_metrics.setdefault(key, []).append((metric_line['time'], value))
        return grouped_metrics

    @staticmethod
    def correct_time(grouped_metrics):
        """
        Correc the times from first epoch time in seconds (set to 0) to last time (minus the first
        time). In other words, put the scale from 0 - (max-min).
        :param grouped_metrics: Metrics grouped on their metric key.
        :return: Grouped metrics with their times corrected.
        """
        metrics = grouped_metrics.copy()
        for metric, metric_values in metrics.items():
            min_time = min([time for (time, _) in metric_values])
            metrics[metric] = [(time - min_time, value) for (time, value) in metric_values]
        return metrics

    @staticmethod
    def plot_metrics(metrics):
        """
        Plot the metrics on a graph.
        :param metrics: Metrics to plot.
        """
        for metric, values in metrics.items():
            plt.plot(*zip(*values), linestyle='-', marker='o')
            plt.title(metric)
            plt.show()


def main():
    parser = Parser()
    metrics = parser.parse('instance_manager.tgz')
    print(metrics)
    parser.plot_metrics(metrics)


if __name__ == "__main__":
    main()
