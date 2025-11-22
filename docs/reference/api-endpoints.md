# API Endpoints Reference

This document shows all API endpoints used by the V2 cache system and what response format we expect.

## Cache Loading Endpoints

### 1. Get Spaces List
**Endpoint**: `/dwaas-core/api/v1/spaces`
**Method**: GET
**From url.json**: `list_of_spaces`
**Used in**: `api_client.get_spaces()`

**Expected Response Format** (please provide example):
```json
// Option A: Direct list
[
  {
    "spaceId": "...",
    "id": "...",
    "label": "..."
  }
]

// Option B: Wrapped in object
{
  "spaces": [
    {
      "spaceId": "...",
      "id": "...",
      "label": "..."
    }
  ]
}
```

**Example file to provide**: `example_spaces_list.json`

---

### 2. Get Space Business Names
**Endpoint**: `/dwaas-core/repository/spaces`
**Method**: GET
**Query Parameters**:
- `inSpaceManagement=true`
- `details=id,name,business_name`

**From url.json**: `spaces_name`
**Used in**: `api_client.get_space_business_names()`

**Expected Response Format** (please provide example):
```json
[
  {
    "qualifiedName": "...",
    "name": "...",
    "businessName": "...",
    "business_name": "..."
  }
]
```

**Example file to provide**: `example_space_names.json`

---

### 3. Get Space Objects (Design Objects)
**Endpoint**: `/deepsea/repository/{spaceID}/designObjects`
**Method**: GET
**From url.json**: `all_design_objects`
**Used in**: `api_client.get_space_objects(space_id)`

**Expected Response Format** (please provide example):
```json
// Based on legacy code, expecting:
{
  "results": [
    {
      "technicalName": "...",
      "qualified_name": "...",
      "name": "...",
      "kind": "...",
      "type": "...",
      "id": "..."
    }
  ]
}
```

**Example file to provide**: `example_design_objects.json`

---

## Lineage Endpoints

### 4. Get Object Dependencies/Lineage
**Endpoint**: `/deepsea/repository/dependencies/`
**Method**: GET
**Query Parameters**:
- `ids={objectId}`
- `recursive=true`
- `impact=true`
- `lineage=true`
- `dependencyTypes=sap.dis.target,csn.entity.association,csn.query.from,...`

**From url.json**: `dependency`
**Used in**: `api_client.get_lineage(object_id)`

**Expected Response Format** (please provide example):
```json
[
  {
    "id": "...",
    "qualifiedName": "...",
    "name": "...",
    "kind": "...",
    "folderId": "...",
    "dependencyType": "...",
    "impact": true/false,
    "lineage": true/false,
    "dependencies": [
      // Recursive structure
    ]
  }
]
```

**Example file to provide**: You already have `API lineage response.txt`

---

## Current Implementation

### api_client.py - get_spaces()
```python
def get_spaces(self) -> List[Space]:
    data = self._make_request("GET", "/dwaas-core/api/v1/spaces")

    # Currently handles:
    # - dict with 'spaces' key
    # - direct list
    # Need to know which one is correct!
```

### api_client.py - get_space_business_names()
```python
def get_space_business_names(self) -> Dict[str, str]:
    params = {
        'inSpaceManagement': 'true',
        'details': 'id,name,business_name'
    }
    data = self._make_request("GET", "/dwaas-core/repository/spaces", params=params)

    # Currently expects list of dicts
    # Need to confirm format!
```

### api_client.py - get_space_objects()
```python
def get_space_objects(self, space_id: str) -> List[DataspherObject]:
    data = self._make_request("GET", f"/deepsea/repository/{space_id}/designObjects")

    # Currently handles:
    # - {'results': [...]}
    # - direct list [...]
    # Based on legacy code, should be {'results': [...]}
```

---

## What We Need From You

Please provide example JSON files for these endpoints:

1. **example_spaces_list.json** - Response from `/dwaas-core/api/v1/spaces`
2. **example_space_names.json** - Response from `/dwaas-core/repository/spaces?inSpaceManagement=true&details=...`
3. **example_design_objects.json** - Response from `/deepsea/repository/{spaceID}/designObjects`

You can either:
- Create these files in the `examples/` folder
- Paste the JSON directly
- Point me to existing response examples

This will help us ensure the parsing logic exactly matches your API responses!
