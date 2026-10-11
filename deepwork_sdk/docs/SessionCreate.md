# SessionCreate


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**title** | **str** |  | 
**duration** | **int** | Scheduled duration in minutes. | 
**goal** | **str** |  | [optional] 

## Example

```python
from deepwork_sdk.models.session_create import SessionCreate

# TODO update the JSON string below
json = "{}"
# create an instance of SessionCreate from a JSON string
session_create_instance = SessionCreate.from_json(json)
# print the JSON string representation of the object
print(SessionCreate.to_json())

# convert the object into a dict
session_create_dict = session_create_instance.to_dict()
# create an instance of SessionCreate from a dict
session_create_from_dict = SessionCreate.from_dict(session_create_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


