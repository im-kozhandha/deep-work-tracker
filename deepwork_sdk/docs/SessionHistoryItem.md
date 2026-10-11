# SessionHistoryItem

Session plus derived timing, filled in by the service layer.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **int** |  | 
**title** | **str** |  | 
**goal** | **str** |  | 
**scheduled_duration** | **int** | Scheduled duration in minutes. | 
**start_time** | **datetime** |  | 
**end_time** | **datetime** |  | 
**status** | [**SessionStatus**](SessionStatus.md) |  | 
**created_at** | **datetime** |  | 
**pause_count** | **int** |  | 
**interruptions** | [**List[InterruptionRead]**](InterruptionRead.md) |  | 
**elapsed_seconds** | **int** | Wall-clock seconds from start to end (or to now if unfinished), including paused time. Null if never started. | [optional] 
**paused_seconds** | **int** | Total seconds spent paused. | [optional] [default to 0]
**focused_seconds** | **int** | elapsed_seconds minus paused_seconds. Null if never started. | [optional] 

## Example

```python
from deepwork_sdk.models.session_history_item import SessionHistoryItem

# TODO update the JSON string below
json = "{}"
# create an instance of SessionHistoryItem from a JSON string
session_history_item_instance = SessionHistoryItem.from_json(json)
# print the JSON string representation of the object
print(SessionHistoryItem.to_json())

# convert the object into a dict
session_history_item_dict = session_history_item_instance.to_dict()
# create an instance of SessionHistoryItem from a dict
session_history_item_from_dict = SessionHistoryItem.from_dict(session_history_item_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


