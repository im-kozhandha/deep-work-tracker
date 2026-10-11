# PauseRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**reason** | **str** | Why the session is being paused (required). | 

## Example

```python
from deepwork_sdk.models.pause_request import PauseRequest

# TODO update the JSON string below
json = "{}"
# create an instance of PauseRequest from a JSON string
pause_request_instance = PauseRequest.from_json(json)
# print the JSON string representation of the object
print(PauseRequest.to_json())

# convert the object into a dict
pause_request_dict = pause_request_instance.to_dict()
# create an instance of PauseRequest from a dict
pause_request_from_dict = PauseRequest.from_dict(pause_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


