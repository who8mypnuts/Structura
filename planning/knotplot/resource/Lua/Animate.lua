--[[

rob scharein
Sunday, 17-Dec-23 22:40:41 UTC

https://easings.net/#easeInOutQuad

--]]

Animate = {}

function Animate.easeInOutQuad2 (x)
  if x < 0.5 then
    return 2 * x * x
  else
    return 1 - math.pow (-2 * x + 2, 2) / 2
  end
end

function Animate.easeInOutQuad (x)
  if x < 0.5 then
    return 2 * x * x
  else
    return 1 - (-2 * x + 2)^2 / 2
  end
end

function Animate.test ()
  for i = 0, 100 do
    local x = i / 100
    print (x .. ": " .. Animate.easeInOutQuad2 (x) .. " " .. Animate.easeInOutQuad (x))
  end
end


