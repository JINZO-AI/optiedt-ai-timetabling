# Known limitations and deliberately excluded features

This list is part of the product definition. Each entry states what is not supported, why,
and what an institution can do instead.

## Deliberately excluded

| Feature | Reason | Workaround / path |
|---|---|---|
| Student sectioning (optimizing individual students into sections) | Target institutions schedule cohort groups; sectioning is a separate optimization problem with its own data (course requests) | Model electives and options as group partitions (ADR 0011) |
| Automatic instructor assignment (deciding who teaches what) | Teaching allocation is a staffing decision made before timetabling | Assign instructors to activities in the data |
| Alternating-week patterns in the weekly solver | Adds per-week conflict reasoning; most target institutions publish one weekly pattern (ADR 0017) | Date-level exceptions for occasional changes; separate groups per alternation |
| Natural-language constraint entry | A misunderstood sentence produces a wrong timetable that looks right | Catalogue-driven rule forms |
| Single sign-on (OIDC/SAML) | Requires an identity provider per institution to test against | Local accounts; identity is separated from credentials for a later provider |
| Multi-institution SaaS tenancy | ADR 0004 | One deployment per institution |
| Native mobile applications | Responsive portal and calendar feeds cover staff and students | iCalendar subscription in the phone's calendar |

## Limitations of this release

The final audit updates this section with measured limits (instance sizes, solve times) from
`docs/benchmarks/`.
