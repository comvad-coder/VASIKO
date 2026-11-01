# Module manifest contract

Каждый manifest содержит:

```text
module_id
name
version
purpose
status
required_skills
allowed_agents
required_integrations
input_contracts
output_contracts
permissions
budget_limits
test_status
activation_status
rollback_version
approval_id
```

`status` проходит lifecycle `idea → description → manifest → draft → test_environment → qa → approval → activation → monitoring`.

`activation_status=active` разрешается только при `test_status=passed` и наличии явного `approval_id`. Запрещены `read_secrets`, `change_own_constraints`, `grant_self_permissions`, `pay_without_approval`, `publish_without_approval` и `change_workspace_without_backup`.
