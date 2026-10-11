# InterruptionRead


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **int** |  | 
**reason** | **str** |  | 
**pause_time** | **datetime** |  | 
**resume_time** | **datetime** |  | 

## Example

```python
from deepwork_sdk.models.interruption_read import InterruptionRead

# TODO update the JSON string below
json = "{}"
# create an instance of InterruptionRead from a JSON string
interruption_read_instance = InterruptionRead.from_json(json)
# print the JSON string representation of the object
print(InterruptionRead.to_json())

# convert the object into a dict
interruption_read_dict = interruption_read_instance.to_dict()
# create an instance of InterruptionRead from a dict
interruption_read_from_dict = InterruptionRead.from_dict(interruption_read_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


