# HistorySummary


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**total_sessions** | **int** |  | 
**status_counts** | **Dict[str, int]** | Count per status; every allowed status is present, zeros included. | 
**completed_count** | **int** |  | 
**completion_rate** | **float** | completed / sessions in a terminal state * 100, rounded to 1 decimal; 0.0 when no session is terminal. | 
**total_interruptions** | **int** |  | 
**total_focused_seconds** | **int** |  | 
**average_focused_seconds_completed** | **float** | Mean focused seconds over completed sessions; null if none. | 

## Example

```python
from deepwork_sdk.models.history_summary import HistorySummary

# TODO update the JSON string below
json = "{}"
# create an instance of HistorySummary from a JSON string
history_summary_instance = HistorySummary.from_json(json)
# print the JSON string representation of the object
print(HistorySummary.to_json())

# convert the object into a dict
history_summary_dict = history_summary_instance.to_dict()
# create an instance of HistorySummary from a dict
history_summary_from_dict = HistorySummary.from_dict(history_summary_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


