# predictive_linuxops_pcp_aap

# 🔮 Predictive DevOps with PCP, Machine Learning & Ansible EDA

This repository implements a **Predictive DevOps pipeline** on Red Hat Enterprise Linux using:

- **Performance Co-Pilot (PCP)** for time-series metric collection.
- **pmrep** for extracting historical data from PCP archives into CSV.
- **Machine Learning (scikit-learn)** for generating linear forecasts.
- **Matplotlib** for data visualization and comparison of observed vs predicted values.
- **Ansible Event Driven Automation (EDA)** to automatically react to predictive conditions or threshold breaches.

---

## 🧭 Repository Structure


| Folder | Description |
|:-------|:-------------|
| `pcp_enable_metrics/` | Configures and enables PCP metrics to be collected in the `pmlogger` archive files. |
| `pmrep_scripts/` | Extracts metrics from `pmlogger` archives into CSV format using `pmrep`. |
| `ml_scripts/` | Contains the machine learning logic — applies linear regression over CSV data to predict future metric values. |
| `matplot_graphs/` | Visualizes both base metrics and observed vs predicted datasets using Matplotlib. |
| `aap_eda/` | Defines rulebooks for **Ansible Event Driven Automation**, enabling automatic responses based on metric predictions. |
| `csv/` | Stores the resulting data files — base (`*_pmrep_final.csv`) and forecast (`forecast_*.csv`). |
| `LICENSE` | Open-source project license. |


## ⚙️ Execution Flow

| Step | Folder | Description | Main Script |
|:----:|:--------|:-------------|:-------------|
| **1** | `pcp_enable_metrics` | Enable PCP metrics and configure which metrics are logged to `pmlogger`. | `write_metric_pmlogfile.txt` |
| **2** | `pmrep_scripts` | Read historical `pmlogger` archives for a given date range and export data to a single consolidated CSV. | `read_pmfiles_concat_in_one_csv.sh` |
| **3** | `ml_scripts` | Apply a **linear regression model** to predict future metric values based on historical data. | `ml_trend.py` |
| **4** | `matplot_graphs` | Generate visualizations for observed metrics or observed vs predicted trends. | `plot_base_pcp_metric.py` / `plot_split_by_observed_predicted.py` |
| **5** | `aap_eda` | Build a **rulebook** to connect predictive metrics to **Ansible EDA**, enabling proactive automated remediation. | `rulebook/` |

---
