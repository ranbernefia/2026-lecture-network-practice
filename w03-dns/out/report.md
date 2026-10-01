# Task 2 - DNS Steering Report

Networks measured: network1, phone

## Chains and third-party classification

| Site | Chain length | Final zone | Third party? | Rule's verdict |
|---|---|---|---|---|
| www.microsoft.com | 2 | e13678.dscb.akamaiedge.net | yes | third party |
| www.netflix.com | 1 | www.prod.ftl.netflix.com | no | not third party |
| www.adobe.com | 2 | a1319.dscr.akamai.net | yes | third party |
| www.cnn.com | 1 | cnn-tls.map.fastly.net | yes | third party |
| www.apple.com | 3 | e6858.dsce9.akamaiedge.net | yes | third party |
| www.korea.ac.kr | 0 | www.korea.ac.kr | no | not third party |
| www.stanford.edu | 1 | stanford.netlifyglobalcdn.com | yes | third party |
| www.bbc.co.uk | 2 | bbc.map.fastly.net | yes | third party |
| www.spotify.com | 1 | atc.spotify.map.fastly.net | yes | third party |
| www.github.com | 1 | github.com | no | not third party |
| www.wikipedia.org | 1 | dyna.wikimedia.org | yes | third party |
| www.nytimes.com | 3 | nytimes.map.fastly.net | yes | third party |

## Steering number

- **[network1]** 8 of 11 CDN-hosted sites answered with a different address set to at least one of the 3 resolvers (system, google, quad9): www.microsoft.com, www.adobe.com, www.cnn.com, www.apple.com, www.bbc.co.uk, www.spotify.com, www.github.com, www.nytimes.com.
- **[phone]** 8 of 11 CDN-hosted sites answered with a different address set to at least one of the 3 resolvers (system, google, quad9): www.microsoft.com, www.adobe.com, www.cnn.com, www.apple.com, www.bbc.co.uk, www.spotify.com, www.github.com, www.nytimes.com.
- **[resolver=system, across networks network1, phone]** 3 of 11 sites answered differently: www.microsoft.com, www.adobe.com, www.apple.com.
- **[resolver=google, across networks network1, phone]** 2 of 11 sites answered differently: www.adobe.com, www.apple.com.
- **[resolver=quad9, across networks network1, phone]** 2 of 11 sites answered differently: www.adobe.com, www.apple.com.

## Where the rule (last two labels) is wrong

- `www.wikipedia.org` - chain ends at wikimedia.org, a *different* registrable domain from wikipedia.org, so the two-label rule calls it third-party. But wikimedia.org is the Wikimedia Foundation's own infrastructure - the same operator as wikipedia.org, just a second domain name they also own. It is the mirror image of the netflix.com case: an organization running its own CDN, except this one happens to live under a domain that fails a same-string test. No amount of string comparison can catch this - it requires knowing who actually owns wikimedia.org.
