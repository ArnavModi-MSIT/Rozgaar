# Public Info Edge transport only. PowerShell 7's Windows HTTP/2 stack is required.
# JSON lines on stdin/stdout; no credentials, browser cookies or applicant actions.
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$ProgressPreference = 'SilentlyContinue'
while ($null -ne ($taskLine = [Console]::ReadLine())) {
    try {
        $taskRequest = $taskLine | ConvertFrom-Json -AsHashtable
        if ($taskRequest.kind -eq 'search') {
            $taskOffset = [int]$taskRequest.offset
            if ($taskOffset -lt 0 -or $taskOffset -gt 10000) { throw 'Invalid search offset' }
            $taskCriteria = @{ paginationStartNo=$taskOffset; selectedCall='sort'; sortCriteria=@{name='modifiedDate';isAscending=$false}; anyOfTheseWords='' }
            $taskForm = @{ filterCri=($taskCriteria | ConvertTo-Json -Compress -Depth 5); domain='careers.infoedge.com'; companyId='MTU1Nzg=' }
            $taskResponse = Invoke-WebRequest -Uri 'https://public.zwayam.com/jobs/search' -Method Post -Form $taskForm -HttpVersion 2.0 -TimeoutSec 15
        } elseif ($taskRequest.kind -eq 'detail') {
            $taskId = [string]$taskRequest.id
            if ($taskId -notmatch '^[0-9]{1,18}$') { throw 'Invalid job ID' }
            $taskBody = @{ jobId=[long]$taskId; companyId=15578; domain='careers.infoedge.com' } | ConvertTo-Json -Compress
            $taskResponse = Invoke-WebRequest -Uri 'https://public.zwayam.com/jobs-service/v1/jobs/careersite' -Method Post -Body $taskBody -ContentType 'application/json' -HttpVersion 2.0 -TimeoutSec 15
        } else { throw 'Unsupported public request' }
        $taskData = $taskResponse.Content | ConvertFrom-Json -AsHashtable -Depth 100
        $taskReply = @{ok=$true; data=$taskData}
    } catch {
        $taskStatus = 0
        if ($null -ne $_.Exception.Response) { $taskStatus = [int]$_.Exception.Response.StatusCode }
        $taskReply = @{ok=$false; error=$_.Exception.Message; status=$taskStatus}
    }
    [Console]::WriteLine(($taskReply | ConvertTo-Json -Compress -Depth 100))
    [Console]::Out.Flush()
}
