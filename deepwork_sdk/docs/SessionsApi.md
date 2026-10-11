# deepwork_sdk.SessionsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**complete_session**](SessionsApi.md#complete_session) | **PATCH** /sessions/{session_id}/complete | Complete an active session
[**get_session_history**](SessionsApi.md#get_session_history) | **GET** /sessions/history | Session history and productivity summary
[**pause_session**](SessionsApi.md#pause_session) | **PATCH** /sessions/{session_id}/pause | Pause an active session
[**resume_session**](SessionsApi.md#resume_session) | **PATCH** /sessions/{session_id}/resume | Resume a paused session
[**schedule_session**](SessionsApi.md#schedule_session) | **POST** /sessions/ | Schedule a session
[**start_session**](SessionsApi.md#start_session) | **PATCH** /sessions/{session_id}/start | Start a scheduled session


# **complete_session**
> SessionRead complete_session(session_id)

Complete an active session

Allowed only from `active`. Sets `completed`, or `overdue` when the wall-clock time since start (pauses included) exceeds 110% of the scheduled duration.

### Example


```python
import deepwork_sdk
from deepwork_sdk.models.session_read import SessionRead
from deepwork_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = deepwork_sdk.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with deepwork_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = deepwork_sdk.SessionsApi(api_client)
    session_id = 56 # int | Identifier of the session.

    try:
        # Complete an active session
        api_response = api_instance.complete_session(session_id)
        print("The response of SessionsApi->complete_session:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SessionsApi->complete_session: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **session_id** | **int**| Identifier of the session. | 

### Return type

[**SessionRead**](SessionRead.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**404** | Session not found. |  -  |
**409** | The action is not allowed in the session&#39;s current state. |  -  |
**500** | Unexpected server or database error. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_session_history**
> HistoryResponse get_session_history()

Session history and productivity summary

Returns every session (newest first) with pause count, interruption reasons, elapsed/paused/focused seconds and a summary including the completion rate. Paused sessions whose pause outlived the abandonment timeout are finalized as `abandoned` before the response is built.

### Example


```python
import deepwork_sdk
from deepwork_sdk.models.history_response import HistoryResponse
from deepwork_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = deepwork_sdk.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with deepwork_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = deepwork_sdk.SessionsApi(api_client)

    try:
        # Session history and productivity summary
        api_response = api_instance.get_session_history()
        print("The response of SessionsApi->get_session_history:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SessionsApi->get_session_history: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**HistoryResponse**](HistoryResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**500** | Unexpected server or database error. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **pause_session**
> SessionRead pause_session(session_id, pause_request)

Pause an active session

Allowed only from `active`; a non-empty `reason` is required. Records an interruption and sets `paused`. A session paused more than three times (the fourth pause) becomes `interrupted`, which is terminal.

### Example


```python
import deepwork_sdk
from deepwork_sdk.models.pause_request import PauseRequest
from deepwork_sdk.models.session_read import SessionRead
from deepwork_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = deepwork_sdk.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with deepwork_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = deepwork_sdk.SessionsApi(api_client)
    session_id = 56 # int | Identifier of the session.
    pause_request = deepwork_sdk.PauseRequest() # PauseRequest | 

    try:
        # Pause an active session
        api_response = api_instance.pause_session(session_id, pause_request)
        print("The response of SessionsApi->pause_session:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SessionsApi->pause_session: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **session_id** | **int**| Identifier of the session. | 
 **pause_request** | [**PauseRequest**](PauseRequest.md)|  | 

### Return type

[**SessionRead**](SessionRead.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**404** | Session not found. |  -  |
**409** | The action is not allowed in the session&#39;s current state. |  -  |
**500** | Unexpected server or database error. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **resume_session**
> SessionRead resume_session(session_id)

Resume a paused session

Allowed only from `paused` and only before the abandonment timeout elapses; afterwards the session is `abandoned` and the request is rejected.

### Example


```python
import deepwork_sdk
from deepwork_sdk.models.session_read import SessionRead
from deepwork_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = deepwork_sdk.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with deepwork_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = deepwork_sdk.SessionsApi(api_client)
    session_id = 56 # int | Identifier of the session.

    try:
        # Resume a paused session
        api_response = api_instance.resume_session(session_id)
        print("The response of SessionsApi->resume_session:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SessionsApi->resume_session: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **session_id** | **int**| Identifier of the session. | 

### Return type

[**SessionRead**](SessionRead.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**404** | Session not found. |  -  |
**409** | The action is not allowed in the session&#39;s current state. |  -  |
**500** | Unexpected server or database error. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **schedule_session**
> SessionRead schedule_session(session_create)

Schedule a session

Creates a session in the `scheduled` state. `duration` is in minutes (1-1440).

### Example


```python
import deepwork_sdk
from deepwork_sdk.models.session_create import SessionCreate
from deepwork_sdk.models.session_read import SessionRead
from deepwork_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = deepwork_sdk.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with deepwork_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = deepwork_sdk.SessionsApi(api_client)
    session_create = deepwork_sdk.SessionCreate() # SessionCreate | 

    try:
        # Schedule a session
        api_response = api_instance.schedule_session(session_create)
        print("The response of SessionsApi->schedule_session:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SessionsApi->schedule_session: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **session_create** | [**SessionCreate**](SessionCreate.md)|  | 

### Return type

[**SessionRead**](SessionRead.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**201** | Successful Response |  -  |
**500** | Unexpected server or database error. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **start_session**
> SessionRead start_session(session_id)

Start a scheduled session

Allowed only from `scheduled`. Records `start_time` and sets `active`.

### Example


```python
import deepwork_sdk
from deepwork_sdk.models.session_read import SessionRead
from deepwork_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = deepwork_sdk.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with deepwork_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = deepwork_sdk.SessionsApi(api_client)
    session_id = 56 # int | Identifier of the session.

    try:
        # Start a scheduled session
        api_response = api_instance.start_session(session_id)
        print("The response of SessionsApi->start_session:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SessionsApi->start_session: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **session_id** | **int**| Identifier of the session. | 

### Return type

[**SessionRead**](SessionRead.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**404** | Session not found. |  -  |
**409** | The action is not allowed in the session&#39;s current state. |  -  |
**500** | Unexpected server or database error. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

