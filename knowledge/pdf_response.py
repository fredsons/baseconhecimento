"""Entrega privada de intervalos de um PDF, após autorização na view."""
import re
from django.http import HttpResponse, StreamingHttpResponse
from django.utils.http import content_disposition_header, http_date, parse_http_date_safe

def serve(request,path,filename,sha256,download=False):
    size=path.stat().st_size
    etag='"'+sha256+'"'
    modified=int(path.stat().st_mtime)
    start,end=0,size-1
    value=request.headers.get('Range','')
    condition=request.headers.get('If-Range')
    if condition and condition!=etag:
        timestamp=parse_http_date_safe(condition)
        if timestamp is None or timestamp<modified: value=''
    partial=False
    if value:
        match=re.fullmatch(r'bytes=(\d{0,20})-(\d{0,20})',value)
        invalid=not match or size==0
        if match:
            lo,hi=match.groups()
            invalid=invalid or not (lo or hi)
            if lo:
                start=int(lo);end=min(int(hi),size-1) if hi else size-1
            elif hi:
                length=int(hi);start=max(0,size-length)
                invalid=invalid or length==0
            invalid=invalid or start>=size or start>end
        if invalid:
            response=HttpResponse(status=416)
            response['Content-Range']=f'bytes */{size}'
            response['Cache-Control']='private, no-store'
            return response
        partial=True
    def chunks():
        with path.open('rb') as file:
            file.seek(start);remaining=end-start+1
            while remaining:
                chunk=file.read(min(65536,remaining))
                if not chunk: break
                remaining-=len(chunk)
                yield chunk
    response=HttpResponse(content_type='application/pdf') if request.method=='HEAD' else StreamingHttpResponse(chunks(),content_type='application/pdf')
    response.status_code=206 if partial else 200
    response['Content-Length']=end-start+1
    response['Accept-Ranges']='bytes'
    response['ETag']=etag
    response['Last-Modified']=http_date(modified)
    response['Content-Disposition']=content_disposition_header(download,filename)
    response['Cache-Control']='private, no-store'
    if partial: response['Content-Range']=f'bytes {start}-{end}/{size}'
    return response
