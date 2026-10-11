# SessionRead


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

## Example

```python
from deepwork_sdk.models.session_read import SessionRead

# TODO update the JSON string below
json = "{}"
# create an instance of SessionRead from a JSON string
session_read_instance = SessionRead.from_json(json)
# print the JSON string representation of the object
print(SessionRead.to_json())

# convert the object into a dict
session_read_dict = session_read_instance.to_dict()
# create an instance of SessionRead from a dict
session_read_from_dict = SessionRead.from_dict(session_read_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


