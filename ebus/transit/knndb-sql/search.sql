select output
from data
order by array_distance(inputs, $inputs :: float4[6])
limit $n;
