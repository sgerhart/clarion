# pxGrid Connection Flow Analysis

## Current Problem

When enabling the connector with ISE admin credentials:
1. `_activate_account()` tries `AccountActivate` with admin credentials → 401
2. Detects username != client_name, calls `_create_account()`
3. `_create_account()` should create the client and return bootstrap password
4. `_authenticate()` is called but fails with 401

## Root Cause

After `AccountCreate` succeeds:
- `_create_account()` sets `self.bootstrap_password` and updates `self.config.password` and `self.config.username`
- BUT this happens INSIDE `_create_account()`, and the changes might not persist when `_authenticate()` is called
- OR `AccountCreate` is failing silently and not returning the bootstrap password

## Current Flow

```
connect()
  ├─ _activate_account()
  │   ├─ Try AccountActivate (with provided credentials)
  │   │   └─ If 401 and username != client_name:
  │   │       └─ Call _create_account()
  │   │           ├─ AccountCreate (with ISE admin credentials)
  │   │           ├─ If success: Set bootstrap_password, update config
  │   │           └─ Return bootstrap_password
  │   └─ If AccountCreate succeeded, config should have client credentials
  │
  ├─ _authenticate()  ← FAILING HERE
  │   └─ Uses self.config.username and self.config.password
  │       └─ Should be client_name and bootstrap_password, but might still be admin credentials
  │
  └─ _get_node_name()
```

## Issues Identified

1. **AccountCreate might be failing**: The logs show "Trying AccountCreate" but no success message
2. **Bootstrap password not persisted**: Even if AccountCreate succeeds, the config updates might not be saved before `_authenticate()` is called
3. **Error handling**: If AccountCreate fails, we should not proceed to `_authenticate()`

## Proposed Solution

1. **Check if AccountCreate is actually succeeding**: Add more logging
2. **Ensure bootstrap password is used**: After AccountCreate succeeds, explicitly update config before calling `_authenticate()`
3. **Don't call `_authenticate()` if AccountCreate fails**: Raise an exception instead

## Next Steps

1. Add detailed logging to `_create_account()` to see what's happening
2. Verify that `AccountCreate` is actually being called and what response we get
3. Check if the bootstrap password is being set correctly
4. Ensure config updates persist before `_authenticate()` is called

