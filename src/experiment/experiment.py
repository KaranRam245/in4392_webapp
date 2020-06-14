import json


class Parser:

    @staticmethod
    def _read_file(filename) -> list:
        with open(filename, 'r') as file:
            return file.readlines()

    def parse(self, filename):
        content = self._read_file(filename)
        metric_lines = self._extract_metrics(content)
        grouped_metrics = self.group_metrics(metric_lines)
        corrected_times = self.correct_time(grouped_metrics)
        print(corrected_times)

    @staticmethod
    def _extract_metrics(content: list):
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
        grouped_metrics = {}
        for metric_line in metric_lines:
            for key, value in metric_line.items():
                if key != 'time':
                    grouped_metrics.setdefault(key, []).append((metric_line['time'], value))
        return grouped_metrics

    @staticmethod
    def correct_time(grouped_metrics):
        metrics = grouped_metrics.copy()
        for metric, metric_values in metrics.items():
            min_time = min([time for (time, _) in metric_values])
            metrics[metric] = [(time - min_time, value) for (time, value) in metric_values]
        return metrics


def main():
    Parser().parse('example.log')


if __name__ == "__main__":
    main()
