# Railway demo configuration

`railway.ts` owns only the `calligraphy-demo` service and its volume in the linked
`charming-magic` project. It uses a named partial so other services are preserved.

See [deployment instructions](../docs/deployment.md) for setup, upload, limits,
font privacy, persistence and verification. Run `railway config plan` before
`railway config apply --yes`, then `railway up --service calligraphy-demo --detach`.
