---
layout: post
title: "Time Series Data Points SVG Animation"
date: 2016-08-04 10:35
comments: true
categories:
---

This silly visualisation (I only learned about SVG animation this
morning) demonstrates what happens when multiple Tgres data points
arrive within the same step (i.e. smallest time interval for this
series). Different tools do different things, e.g. Graphite simply
discards all points but the last, while Tgres does the same thing as
RRDTool by computing a weighted average.

Let's say we have a series with a step of 100 seconds. We receive the
following data points:

| Time  | Value |
|-------|-------|
|  25s  | 1.0   |
|  75s  | 3.0   |
| 100s  | 2.0   |


Tgres adds this up to 1.6875 for the 100s step. Why?

One way to think about it is that the incomplete step is an empty
swimming pool as wide as 1 step, into which we dump blocks of
water. The first data point dumps a 2.0 x 0.25 block of water, which
fills the pool to 0.375. The second data point dumps a 3.0 x 0.50
block, which raises the water level to 1.5. The last data point dumps
a 1.0 x 0.25 block which raises it to the final value of 1.6875.

<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width='400px' height='150px'>

<title>Small SVG example</title>

<svg x='50'>
<polyline points='5 25, 5 100, 105 100, 105 25' stroke-width='4' stroke="black" style='fill: none;' />


<svg x="5">

<text x="156" y="115" font-family="Verdana" font-size="12" style="fill:green;">click to start</text>
<rect id="startbox" x="150" y="100" width="90" height="20" stroke="green" fill="transparent" />

<line x1='0' y1='0' x2='0' y1='150' stroke='red'>
  <animate attributeName='x1' from='0' to='100' begin='0' dur='10s' fill="freeze" begin="startbox.click" />
  <animate attributeName='x2' from='0' to='100' begin='0' dur='10s' fill="freeze" begin="startbox.click" />
</line>

<!-- data points and values -->

<text x="25" y="46" font-family="Verdana" font-size="10" style="visibility:hidden">
2.0
  <animate attributeType="CSS" attributeName="visibility" begin="startbox.click"
    from="hidden" to="visible"
    dur="10s"
    values="hidden; visible; visible"
    keyTimes="0; 0.25; 1"
    fill="freeze" />
</text>
<circle cx="25" cy="50" r="3" fill="blue" style="visibility:hidden">
  <animate attributeType="CSS" attributeName="visibility" begin="startbox.click"
    from="hidden" to="visible"
    dur="10s"
    values="hidden; visible; visible"
    keyTimes="0; 0.25; 1"
    fill="freeze" />
</circle>
<rect x="0" y="50" width="25" height="50" fill="transparent" stroke="blue" style="visibility: hidden;">
  <animate attributeType="CSS" attributeName="visibility" begin="startbox.click"
    from="hidden" to="visible"
    dur="10s"
    values="hidden; visible; visible"
    keyTimes="0; 0.25; 1"
    fill="freeze" />
</rect>
<rect x="0" y="87.5" width="100" height="12.5" fill="#aed6f1" stroke="transparent" fill-opacity="0.4" style="visibility: hidden;">
  <animate attributeType="CSS" attributeName="visibility" begin="startbox.click"
    from="hidden" to="visible"
    dur="10s"
    values="hidden; visible; visible"
    keyTimes="0; 0.25; 1"
    fill="freeze" />
</rect>
<text x="105" y="89.5" font-family="Verdana" font-size="10" font-weight="bold" style="visibility:hidden">
 0.375
  <animate attributeType="CSS" attributeName="visibility" begin="startbox.click"
    from="hidden" to="hidden"
    dur="10s"
    values="hidden; visible; hidden; hidden"
    keyTimes="0; 0.25; 0.75; 1"
    fill="freeze" />
</text>

<text x="75" y="22" font-family="Verdana" font-size="10" style="visibility:hidden">
3.0
  <animate attributeType="CSS" attributeName="visibility" begin="startbox.click"
    from="hidden" to="visible"
    dur="10s"
    values="hidden; visible; visible"
    keyTimes="0; 0.75; 1"
    fill="freeze" />
</text>
<circle cx="75" cy="25" r="3" fill="blue" style="visibility:hidden">
  <animate attributeType="CSS" attributeName="visibility" begin="startbox.click"
    from="hidden" to="visible"
    dur="10s"
    values="hidden; visible; visible"
    keyTimes="0; 0.75; 1"
    fill="freeze" />
</circle>
<rect x="25" y="25" width="50" height="75" fill="transparent" stroke="blue" style="visibility: hidden;">
  <animate attributeType="CSS" attributeName="visibility" begin="startbox.click"
    from="hidden" to="visible"
    dur="10s"
    values="hidden; visible; visible"
    keyTimes="0; 0.75; 1"
    fill="freeze" />
</rect>
<rect x="0" y="50" width="100" height="50" fill="#aed6f1" stroke="transparent" fill-opacity="0.4" style="visibility: hidden;">
  <animate attributeType="CSS" attributeName="visibility" begin="startbox.click"
    from="hidden" to="visible"
    dur="10s"
    values="hidden; visible; visible"
    keyTimes="0; 0.75; 1"
    fill="freeze" />
</rect>
<text x="105" y="52" font-family="Verdana" font-size="10" font-weight="bold" style="visibility:hidden">
 1.5
  <animate attributeType="CSS" attributeName="visibility" begin="startbox.click"
    from="hidden" to="hidden"
    dur="10s"
    values="hidden; visible; hidden"
    keyTimes="0; 0.75; 1"
    fill="freeze" />
</text>

<text x="100" y="72" font-family="Verdana" font-size="10" style="visibility:hidden">
1.0
  <animate attributeType="CSS" attributeName="visibility" begin="startbox.click"
    from="hidden" to="visible"
    dur="10s"
    values="hidden; visible; visible"
    keyTimes="0; 1; 1"
    fill="freeze" />
</text>
<circle cx="100" cy="75" r="3" fill="blue" style="visibility:hidden">
  <animate attributeType="CSS" attributeName="visibility" begin="startbox.click"
    from="hidden" to="visible"
    dur="10s"
    values="hidden; visible; visible"
    keyTimes="0; 1; 1"
    fill="freeze" />
</circle>
<rect x="75" y="75" width="25" height="25" fill="transparent" stroke="blue" style="visibility: hidden;">
  <animate attributeType="CSS" attributeName="visibility" begin="startbox.click"
    from="hidden" to="visible"
    dur="10s"
    values="hidden; visible; visible"
    keyTimes="0; 1; 1"
    fill="freeze" />
</rect>
<rect x="0" y="43.75" width="100" height="56.25" fill="#aed6f1" stroke="transparent" fill-opacity="0.4" style="visibility: hidden;">
  <animate attributeType="CSS" attributeName="visibility" begin="startbox.click"
    from="hidden" to="visible"
    dur="10s"
    values="hidden; visible; visible"
    keyTimes="0; 1; 1"
    fill="freeze" />
</rect>
<text x="105" y="45.75" font-family="Verdana" font-size="10" font-weight="bold" style="visibility:hidden">
 1.6875
  <animate attributeType="CSS" attributeName="visibility" begin="startbox.click"
    from="hidden" to="visible"
    dur="10s"
    values="hidden; visible; visible"
    keyTimes="0; 1; 1"
    fill="freeze" />
</text>
</svg>
</svg>
</svg>

Compare this with Graphite which would simply discard the first two
data points and we are left with 1.0 as the final value.

Why is this important? Because this is how rates add up. If this was
speed of a car in meters per second (more like a bycicle, I guess),
its weighted average speed for the duration of this step of 1.6875
meters per second would mean that in the 100s it would have traveled
exactly 168.75 meters.
