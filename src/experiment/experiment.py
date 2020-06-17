import json
import statistics
import tarfile

import matplotlib.pyplot as plt
import numpy as np


class Parser:

    @staticmethod
    def _read_file(filename) -> list:
        """
        Read the given file.
        :param filename:
        :return:
        """
        content = []
        with tarfile.open(filename, 'r') as tar:
            for member in tar.getmembers():
                file = tar.extractfile(member)
                content += [line.decode('utf-8') for line in file.readlines()]
        return content

    def parse(self, filename):
        """
        Read a file, convert the lines to metrics, group the metrics and correct the times.
        :param filename: File to extract.
        :return: Metrics with corrected times.
        """
        content = self._read_file(filename)
        with open('total_log.txt', 'w') as file:
            file.writelines(content)
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
    def plot_metrics(metrics, **kwargs):
        """
        Plot the metrics on a graph.
        :param metrics: Metrics to plot.
        """
        for metric, values in metrics.items():
            x_values, y_values = zip(*values)
            Parser._plot(x_values, y_values, title=metric, **kwargs)

    @staticmethod
    def _plot(x_values, y_values, title='', xlabel='', ylabel='', int_yticks=False):
        plt.plot(x_values, y_values, linestyle='-', marker='o')
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        if int_yticks:
            rnge = range(0, max(y_values) + 1)
            plt.yticks(ticks=rnge, labels=list(rnge))
        plt.show()

    @staticmethod
    def statistics(metrics, rounding=2):
        for metric, values in metrics.items():
            _, y_values = zip(*values)
            print(
                """Statistics report [{}]:
                    - Min    : {}
                    - Q1     : {}
                    - Average: {}
                    - Median : {}
                    - Q3     : {}
                    - Max    : {}
                """.format(metric,
                           round(min(y_values), rounding),
                           round(np.percentile(y_values, 25), rounding),
                           round(statistics.mean(y_values), rounding),
                           round(statistics.median(y_values), rounding),
                           round(np.percentile(y_values, 75), rounding),
                           round(max(y_values), rounding)
                           )
            )

    @staticmethod
    def charge_time(metrics, rounding=2):
        for _, values in metrics.items():
            _, y_values = zip(*values)
            charge_times = {}
            for y_value in y_values:
                instance_id = y_value['instance_id']
                charged = y_value['charged']
                charge_times[instance_id] = charge_times.get(instance_id, 0) + charged
            total_time = round(sum(charge_times.values()), rounding)
            charge_times = {key: round(value, rounding) for key, value in charge_times.items()}
            print("Charge time:\n  - Total: {} seconds\n  - Individual: {}".format(total_time,
                                                                                   charge_times))

    @staticmethod
    def plot_heartbeats(metrics, hb_keys, ylabels, keep_instances=None, titles=None,
                        same_figure=False, alt_labels=None, replace_id=None):
        for _, values in metrics.items():  # This loop always runs once (metrics=['heartbeat']).
            _, heartbeats = zip(*values)
            heartbeats = [(heartbeat['time'], heartbeat['instance_id'], heartbeat) for heartbeat in
                          heartbeats]
            heartbeat_dict = {}  # Heartbeats grouped per instance.
            for time, instance_id, heartbeat in heartbeats:
                heartbeat_dict.setdefault(instance_id, []).append((time, heartbeat))

            for idx, key in enumerate(hb_keys):
                lines = []
                for instance_id, inst_values in heartbeat_dict.items():
                    if keep_instances and instance_id not in keep_instances:
                        continue
                    metric_values = [(time, heartbeat[key]) for time, heartbeat in inst_values]
                    lines.append((instance_id, metric_values))
                flat_lines = [item for sublist in [line for _, line in lines] for item in sublist]
                min_time = min([time for time, _ in flat_lines])
                if same_figure:
                    if not titles:
                        print("YOU MUST SPECIFY TITLES WITH SAME FIGURE!")
                    title = titles[0]  # Must specify a title
                    show = idx == (len(hb_keys) - 1)
                    ylabel = ylabels[0]
                else:
                    title = titles[idx] if titles else key
                    show = True
                    ylabel = ylabels[idx]
                alt_label = None if not alt_labels else alt_labels[idx]
                Parser._heartbeat_lines(lines, min_time=min_time, title=title, ylabel=ylabel,
                                        show=show, alt_label=alt_label, replace_id=replace_id)

    @staticmethod
    def _heartbeat_lines(lines, min_time, title='', ylabel='', show=True, alt_label=None,
                         replace_id={}):
        for instance_id, values in lines:
            times, y_values = zip(*values)
            times = [time - min_time for time in times]
            label = alt_label if alt_label else replace_id.get(instance_id, instance_id)
            plt.plot(times, y_values, linestyle='-', marker='o', label=label)
        if show:
            plt.title(title)
            plt.xlabel("Time (in seconds)")
            plt.ylabel(ylabel)
            plt.legend()
            plt.show()

    @staticmethod
    def process(metrics, keys: list, func, **kwargs):
        global PROCESSED
        metrics = {key: value for key, value in metrics.items() if key in keys}
        func(metrics, **kwargs)
        for key in keys:
            PROCESSED[key] = True


PROCESSED = {}
NODE_MANAGER = 'i-0b5222c31dc02418c'


def main():
    global PROCESSED, NODE_MANAGER
    parser = Parser()
    metrics = parser.parse('instance_manager.tgz')
    # pprint.PrettyPrinter(indent=4).pprint(metrics)
    PROCESSED = dict.fromkeys(list(metrics.keys()), False)
    parser.process(metrics, ['workers'], parser.plot_metrics,
                   xlabel='Time (in seconds)', ylabel='Workers running',
                   int_yticks=True)
    parser.process(metrics, ['upload_duration'],
                   parser.statistics)
    parser.process(metrics, ['charged_time'],
                   parser.charge_time)
    parser.process(metrics, ['heartbeat'], parser.plot_heartbeats,
                   hb_keys=['cpu_usage', 'mem_usage'],
                   ylabels=['CPU usage (in %)', 'RAM usage (in %)'],
                   replace_id={NODE_MANAGER: 'node_manager'},
                   titles=['CPU usage in instances', 'Memory usage in instances'])
    parser.process(metrics, ['heartbeat'], parser.plot_heartbeats,
                   hb_keys=['tasks_waiting', 'tasks_running'],
                   ylabels=['Tasks'],
                   keep_instances=[NODE_MANAGER],
                   titles=['Tasks waiting and running in Node Manager'],
                   alt_labels=['Tasks waiting', 'Tasks running'],
                   same_figure=True)
    print("Metrics processed: {}".format(PROCESSED))


if __name__ == "__main__":
    main()
