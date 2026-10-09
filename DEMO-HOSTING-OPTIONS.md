# Demo hosting options and monthly estimate

Pricing checked on **9 October 2026**, in **USD per month**, excluding model
usage. This is a planning estimate for the fictional-data demo. No provider,
subscription, deployment or spending has been approved by this document.

## Recommendation

Keep the existing local installation for the first volunteer/trainer pilot.
There is no demonstrated remote-access requirement yet. If invited remote access
becomes necessary, evaluate **Render's paid 512 MB instance with a persistent
disk first**: its estimated application/storage baseline is **$7.25/month**.
This recommendation is our assessment of pricing and operational fit, not a
tested deployment or an all-inclusive service quote.

Railway Hobby is an alternative when measured resource use makes its metered
bill attractive. It has a $5 monthly floor, but current volume permissions
conflict with our non-root container and need a reviewed solution. Neither host
has been rehearsed with this application. The owner chooses the provider and
budget after reviewing access, recovery, capacity and total cost.

## What is being estimated

One always-running Docker service, one Uvicorn worker, one persistent SQLite
data directory, fictional records and a small supervised pilot. Start in
`AGENT_MODE=demo`, without model credentials. No separate database service,
replica, staging environment or background worker is included.

The small memory tier and Railway average-use scenarios below are **assumptions**.
We have not measured hosted memory peaks, concurrent-user capacity, outbound
traffic or recovery duration. The pilot plan's 5–10 participants does not establish
that a 512 MB instance can support that many simultaneous active users.

| Option | Application/storage estimate | Fit and remaining work |
| --- | --- | --- |
| Existing local Python or Compose demo | $0 additional hosting subscription | Best initial choice; operator supplies the computer, availability and private backups. Electricity, hardware and operator time still have costs. |
| Render paid 512 MB instance + 1 GB disk, Hobby workspace | $7.25 baseline | More predictable compute bill; verify capacity, writable mount, access boundary, proxy behavior and managed-host recovery. |
| Railway Hobby + volume | $5 floor; illustrative scenarios $5–$13.25 | Actual usage determines the bill; resolve non-root volume compatibility and verify the same access/recovery requirements. |

These are application/storage subtotals. Access protection, independent backup
storage, domains, taxes, model usage and operator/support time are additional
unless separately established as included. No trial or promotional credits are
used to calculate a continuing monthly price.

## Render estimate

The listed paid 512 MB instance costs $7/month; persistent disk capacity costs
$0.25/GB/month. A Hobby workspace has no plan fee and includes 5 GB outbound
bandwidth and 500 standard build minutes shared across the workspace. Additional
bandwidth costs $0.15/GB, and additional standard build minutes cost $5 per 1,000.
Recheck these rates before purchase. Sources: [Render pricing](https://render.com/pricing),
[workspace plan features](https://render.com/docs/platform-features-by-plan),
[build pipeline](https://render.com/docs/build-pipeline).

| Scenario | Calculation | Monthly subtotal |
| --- | --- | --- |
| Small baseline | $7 compute + 1 GB disk × $0.25 | **$7.25** |
| More reserved disk | $7 + 5 GB disk × $0.25 | **$8.25** |
| More outbound traffic | Baseline + (20 − 5) GB × $0.15 | **$9.50** |
| Memory upgrade if needed | $25 listed 2 GB instance + 1 GB disk × $0.25 | **$25.25** |

Each scenario assumes one service for the whole month, a Hobby workspace with
no other use of its allowances, and builds within the included minutes. Disk
charges use provisioned capacity. The $25.25 case shows that a memory upgrade can
change the budget materially; it is not a measured requirement.

Only mounted paths persist. A disk attaches to one instance, prevents horizontal
scaling and causes deployment downtime. Daily disk snapshots are not a substitute
for our database-consistent backup and tested restore; Render cautions against
disk-snapshot recovery for custom databases.
[Persistent disk documentation](https://render.com/docs/disks).

Render Free cannot attach a persistent disk and its ephemeral files can disappear
on restart/redeploy; it also sleeps after inactivity. It does not meet this demo's
durable SQLite requirement. [Free service limitations](https://render.com/docs/free).

## Railway estimate

Hobby's $5/month subscription includes $5 of resource usage: estimated total is
`max($5, resource usage)`, rather than $5 plus the full resource bill. Listed rates
are RAM $10/GB/month, CPU $20/vCPU/month, used volume storage $0.15/GB/month and
outbound traffic $0.05/GB. Compute is metered over time.
[Railway pricing](https://docs.railway.com/pricing).

For these illustrative full-month averages:

`resource usage = average RAM GB × $10 + average CPU vCPU × $20 + used disk GB × $0.15 + outbound GB × $0.05`

| Scenario assumption | RAM | CPU | Used disk | Outbound | Resource subtotal | Hobby invoice estimate |
| --- | --- | --- | --- | --- | --- | --- |
| Low average use | 0.25 GB | 0.02 vCPU | 1 GB | 1 GB | $2.50 + $0.40 + $0.15 + $0.05 = $3.10 | **$5.00** |
| Middle illustration | 0.50 GB | 0.05 vCPU | 1 GB | 1 GB | $5.00 + $1.00 + $0.15 + $0.05 = $6.20 | **$6.20** |
| Higher illustration | 1.00 GB | 0.10 vCPU | 5 GB | 10 GB | $10.00 + $2.00 + $0.75 + $0.50 = $13.25 | **$13.25** |

These are scenarios, not a forecast or guaranteed maximum. Account for filesystem
metadata in used disk, other billable account services and any selected backup
charges. Peak memory still determines whether the service stays healthy even
when its average bill is small.

Railway volumes bill used storage, allow one volume per service, disallow replicas
and cause brief redeploy downtime. Its documentation warns that images running
as a non-root UID have mounted-volume permission issues; our image uses UID 10001.
The documented root-user workaround would change our container's security model.
Do not apply it automatically: investigate a supported way to retain non-root
operation, or bring an explicit tradeoff back for review before selecting Railway.
[Railway volume reference](https://docs.railway.com/volumes/reference).

## Access, recovery and cost prerequisites

The following work applies after provider selection and before inviting remote users:

1. **Restrict access.** Current demo account passwords are public in the README.
   Require an approved access gateway or private access arrangement covering the
   entire service, including APIs and documentation. Verify the provider's original
   service URL cannot bypass it. Provider-console authentication does not protect
   the app. Price the chosen boundary separately; it is not included above.
2. **Persist all data.** Mount the complete `/app/data` directory and set
   `TRAINING_DB=/app/data/training.db`; rehearsal databases are stored beside it.
   Verify ownership permits UID 10001 to write, and verify persistence after restart
   and redeploy. Keep a single instance and worker. Docker Compose's localhost
   binding, read-only filesystem and other controls do not automatically transfer
   to a managed service.
3. **Verify routing and sessions.** Route to the image's port 8000, use `/ready` for
   readiness and check `/health` for liveness. Verify HTTPS, trusted proxy behavior
   and a Secure session cookie through the selected ingress. The application derives
   that cookie flag from the request scheme; provider TLS alone does not prove it.
   Check provider logs for sensitive request content as well as application logs.
4. **Adapt recovery.** Convert the stopped-app whole-data-directory backup procedure
   in [DEMO-DEPLOYMENT.md](DEMO-DEPLOYMENT.md) into provider-specific instructions.
   Include rehearsal files and SQLite companion files. Arrange a private copy outside
   the service/account failure boundary, retention and a responsible operator.
   Rehearse restore into empty storage and rollback with the matching old backup and
   reviewed image. Existing local Docker commands are not a managed-host runbook.
5. **Measure and control cost.** Measure startup and peak memory, CPU, data growth and
   latency under the planned pilot workload; record actual usage before expanding.
   Add the access and backup quotes to a total, then agree the budget cap and response
   with the owner. Keep automatic deployment from `dev`/`master` disabled until an
   owner-approved release process exists; deploy only the chosen reviewed revision.

Render has a spend limit for **build minutes**, which can stop further builds;
it is not an account-wide compute/storage/bandwidth cap.
[Build pipeline spend controls](https://render.com/docs/build-pipeline).
Railway distinguishes notification thresholds from a hard compute-usage limit;
reaching that hard limit takes workloads offline. Confirm which charges a selected
limit covers and plan the outage response rather than treating an alert as enforcement.
[Railway cost control](https://docs.railway.com/pricing/cost-control).

## Owner decision record

Keep the completed record private with the [release handover](DEMO-RELEASE-CHECKLIST.md).
Record the remote-demo reason, provider/region, reviewed full source commit, plan,
measured resource needs, access boundary, backup destination/retention, expected
monthly total and exclusions, budget controls, operator and approval date. Recheck
prices and feature availability in that region before approval.

After approval, implement the provider configuration and adapted runbook on a branch
from `dev`, request review in a PR to `dev`, and collect deployment/persistence,
restricted-access, restore and rollback evidence. Only the owner merges and promotes
to production `master`. The first human pilot and actual operator recovery record
remain outstanding. Company production requirements stay in
[PRODUCT-DELIVERY-PLAN.md](PRODUCT-DELIVERY-PLAN.md); this estimate does not satisfy them.
