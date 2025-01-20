# Avoiding test definition duplication

You may find that your test definitions are very similar to each other,  e.g. they all have the same metrics. Instead 
of copy-pasting the definitions  you can use templating capability built-in hunter to define the common bits of configs 
separately.

First, extract the common pieces to the `templates` section:
```yaml
templates:
  common-metrics:
    throughput: 
      suffix: client.throughput
    response-time:
      suffix: client.p50
      direction: -1    # lower is better
    cpu-load: 
      suffix: server.cpu
      direction: -1    # lower is better
```

Next you can recall a template in the `inherit` property of the test:

```yaml
my-product.test-1:
  type: graphite
  tags: [perf-test, daily, my-product, test-1]
  prefix: performance-tests.daily.my-product.test-1
  inherit: common-metrics
my-product.test-2:
  type: graphite
  tags: [perf-test, daily, my-product, test-2]
  prefix: performance-tests.daily.my-product.test-2
  inherit: common-metrics
```

You can inherit more than one template.