from clicky.guidance import hints,spoken_text


def test_guidance_maps_reviewed_capture_pixels_at_fractional_scale_and_offset():
    capture={'bounds':{'x':-1280,'y':120,'width':1280,'height':720},'pixels':{'width':1920,'height':1080}}
    assert hints('Try [POINT:960,540:Settings]',capture)==[{'x':-640,'y':480,'label':'Settings'}]
    assert hints('[TYPE:960,540:Search field]',capture)[0]['label']=='Search field'
    assert spoken_text('Try [POINT:960,540:Settings]')=='Try Settings'


def test_no_guidance_without_capture_or_outside_reviewed_bounds():
    c={'bounds':{'x':0,'y':0,'width':100,'height':100},'pixels':{'width':200,'height':200}}
    assert hints('[POINT:20,30:Click]',None)==[]
    assert hints('[POINT:-1,20:bad] [POINT:200,200:bad] [POINT:nan,0:bad]',c)==[]
    assert len(hints(' '.join('[POINT:1,1:hello]' for _ in range(20)),c))==8
