from json import loads as json_loads
import json
from time import sleep
from typing import Dict, List

import click
import pystac
import requests
from google.cloud import storage

# from hatfieldcmr.metadata.stac.stac_client import StacClient
from hatfieldcmr.metadata.traverse import form_prefixes, group_blobs
from hatfieldcmr.ingest.file_type import MODISBlobType
from hatfieldcmr.ingest.name import BlobPathMetadata
from hatfieldcmr.metadata.stac.itemparse.cmr import CMR2STACItemParser
from hatfieldcmr.metadata.stac.stac_client import StacClient

PROXY_LINK = 'https://gp.geoanalytics.ca'


def create_stac_assets(blob_group: Dict):
    assets_list = []
    assets_meta_list = [{
        'blob_type': MODISBlobType.METADATA_JSON.name,
        'asset_name': 'cmr-metadata',
        'title': 'CMR Metadata',
        'media_type': 'application/json'
    }, {
        'blob_type': MODISBlobType.METADATA_XML.name,
        'asset_name': 'lpdaac-metadata',
        'title': 'LP-DAAC Metadata',
        'media_type': 'text/xml'
    }, {
        'blob_type': MODISBlobType.THUMBNAIL.name,
        'asset_name': 'thumbnail',
        'title': 'Thumbnail',
        'media_type': 'image/jpeg'
    }, {
        'blob_type': MODISBlobType.DATA_HDF.name,
        'asset_name': 'analytic',
        'title': 'Granule',
        'media_type': 'application/x-hdfeos'
    }, {
        'blob_type': MODISBlobType.GEOTIFF.name,
        'asset_name': 'Raster',
        'title': 'GeoTIFF',
        'media_type': 'image/tiff'
    }, {
        'blob_type': MODISBlobType.GEOTIFF_XML,
        'asset_name': 'Raster Metadata',
        'title': 'GeoTIFF Metadata',
        'media_type': 'text/xml'
    }]
    for asset_to_add in assets_meta_list:
        blob_type = asset_to_add['blob_type']
        if blob_type in blob_group:
            blob = blob_group[blob_type]
            #asset = pystac.Asset(blob.self_link,
            asset = pystac.Asset(format_proxy_link(blob.name),
                                 title=asset_to_add['title'],
                                 media_type=asset_to_add['media_type'])
            # item.add_asset(asset_to_add['asset_name'], asset)
            assets_list.append((asset_to_add['asset_name'], asset))
    return assets_list


def format_proxy_link(blob_name):
    return f'{PROXY_LINK}?object={blob_name}'

def filter_non_processed_files(blobs):
    blobs = list(blobs)
    non_processed = []
    for b in blobs:
        if not 'processed/' in b.name:
            non_processed.append(b)
    return non_processed

def update_metadata_entries(gcs_client, stac_client, bucket_name, prefix: str, is_processed:bool = False):
    prefix_metadata = BlobPathMetadata.parse(prefix)

    blobs = gcs_client.list_blobs(bucket_name, prefix=prefix)
    blobs = filter_non_processed_files(blobs)    
    blob_groups_dict = group_blobs(blobs)
    for blob_id in blob_groups_dict:
        group = blob_groups_dict[blob_id]
        if MODISBlobType.METADATA_JSON.name in group:
            json_blob = group[MODISBlobType.METADATA_JSON.name]
            json_data = json_blob.download_as_string()
            meta = json_loads(json_data)
            stac_item = CMR2STACItemParser.parse(
                blob_id, prefix_metadata.product_name_without_version, meta)
            assets_to_add = create_stac_assets(group)
            for asset in assets_to_add:
                stac_item.add_asset(asset[0], asset[1])
            #print(f'adding metadata for {blob_id}')
            stac_client.add_item(stac_item.collection_id, stac_item.to_dict())
    return len(blobs)
@click.command()
@click.option('--stac-url', default='https://stac.geoanalytics.ca')
@click.option('--bucket-name', default='granule-gcs-mtl01')
@click.option('--service-account-json-path', default='', type=click.Path(exists=True), help='file path to service account json')
@click.option('--auth-token', default='', help='OAuth2 Token for STAC API HTTP calls')
@click.option('--gcs-proxy-link', default='https://gp.geoanalytics.ca')
@click.option('--dry-run', default=False, is_flag=True)
@click.argument('start_date', required=True)
@click.argument('end_date', required=True)
@click.argument('products', nargs=-1)
def entry(stac_url: str,
        bucket_name: str,
        service_account_json_path: str,
        auth_token: str, 
        gcs_proxy_link: str,
        dry_run: bool,
        start_date: str,
        end_date: str,
        products: List[str]):
        main(
            stac_url,
            bucket_name,
            service_account_json_path,
            auth_token,
            gcs_proxy_link,
            dry_run,
            start_date,
            end_date,
            products
        )
def main(stac_url: str,
        bucket_name: str,
        service_account_json_path: str,
        auth_token: str, 
        gcs_proxy_link: str,
        dry_run: bool,
        start_date: str,
        end_date: str,
        products: List[str]):
    if service_account_json_path == '':
        gcs_client = storage.Client()
    else:
        gcs_client = storage.Client.from_service_account_json(service_account_json_path)
    
    if auth_token == '':
        auth_token = 'eyJBY2Nlc3NUb2tlbiI6IkV5TExEd0VERnFMb05iNkp1UUtHanpOK3VFUWhaSzRXK3g5cE5KaUtZMUdkQVl0SElVWnNLbUJkc1V2cG8yL2xnOXlWS3ZzTU9ISlhLOVdwTWJlcGxNWjQ2S3FWd0xBdHA3SUZnREREYzRLeDZ6cUE0Q2piWVhNVDNjclN3N1VmMEcvRDZzS0JqQXFpcUUrMjV5T1BSdzJZdW9UZ3lVS1RyTnl1bnRZWjU2bDNsRkVHSW9PeXVXQ09GUDJrbzcrSjlVYVBndmJTSlI4NVhweWFWZEtpdFpuZDY1QmV5empVOE5TNXp6Q2NJWG1GNjlxR2xsbTZTeW9QWVg0cFlMUHQrNU9qcExRa2kxZFBkenRmZHVyam80bCt4RE5nVUxCSVYvbjU0M0w0OWUrRHFxek9Vc1RETE8veU5sZk1Iak91bkNDTk9BcVBsbmdKWDRnQm9RMUd3SzJsUVVyU0VKMlZKZC82R1gvQXlBUW1FVTRrWXpKNEdUUEhCYmp3TXVsR2lOcCtEbDZXVzl4S2ZvelVaUlluU3VBVWNvNDE2cnA0QkFFeThTRk52MkNIeVZVdlF2RGZ5YmZEaWJxY1VSMTI3ZFRFTWJFMlhTWlM5ZUFuNmJPQk8rVXc3VXJoWXBhWTZ1T1BMNDZ5WVBxTmJVbk9mYnEraFVNSmJkU1ZlenBlUjRWaDhPQm1CejN6R25oZWVwMTdOUE1jRUpnUC9ySVpyTFE2bFQzc1FUMU5hTXlJd2VzWGpZWWo0WUN0eEVxZXlYdVRPbEhuay9BZUE5bFVrSjQrZ1dJd3RiMUliaUgxbjUyYjhURTVOYUdsOGViSHo0YXZJM2hrV2JHMmtSazIybU5PV1kxa0tZM2xkRmJyRHBrUGRIYmx6bVVLTitUOWNCYUxJRlNmYVRIR0srQjBmemNjSWY0ankrM1JGQ1hGWkFZT0ZRZ084bkp6Yld1d3BSYW5sbENJK2xiSUc5bGxHTkVLajF6RzVLYlE2M0l5VHZyQ2x6b3FZTWlEbmFyeDVGWlF2RjMxbjQxZGRDTnBBTzl0bFJtU1lzYVRVSHZUSzZGcVo4ampSdGdzN0RLVUdaQi9yY2dMTVJpS3N5RWxqd1duekNlWVc1djlIbEtmdE1rU0ZZcUJLWjhDVHJOQVEyakVZSngzUmc0R2c0NXZBVGtXTEFSY1NLVFBJMUR0WWlwL3JGSmRoOUNpRGEvLzQ5Q1N3OWYrTlkvVUNYemh2R2VtaFg3ZllCNHNPT2g5WkJuMkZ5c2pFSGUreFF3WnhlT1V1MnJ1U0lnc3JRV2ZYT21DU3lhdTJ4enBTYkRXRjdJYk9QL2hDSGpMNGMwTW5jY2lHMEVYUmtJcGpHWDh1eWdHNUxienIzSHAzYkN5cHR0MjAxS2R4azZyK2I1c1hLTzVxemwvRW5jSmVDS3JKMzZmV01VRDhnbE53K2xBYXlHR3BWbVV4VVp6RmtQTjZld2thZHM9IiwiSURUb2tlbiI6IlNJUUtWNDBvbkZzazRHWXdOZzVMZlhDVXdxU0NXWlJ5VzBQUllaRkxvdjlkc3VJK3RGVURzQVJHZHVkNlVBMldWQUljc2VTekxxbVR5YUkxTGU5SmFNRUFIR2x6MVN1MkY3T0FPN2Z6VFlEejRBRUQ2cEpibDFwcjN5L3M0cGU5NnA3MjBNV3hDaXRGZWdKNzM1UVpDblpJeWpKRFhLemZ3UTMvSis3bzAvWlhIV254WDFDY25LeXNzSzNxLzk0dCsrVXRDWnF3ZVJKM3l1U3VqdHZEZktYQ2RkNk1Sem5OOEN6dEF6Y0U2NE94ZVJJUWZuQXpveGhMK1VQM1lObnVveTFUQUtMOTMyNWV6L0FPS3VrZkpvajhzNGY3elNJLy8xL2JDbzl1VUpSWnRkZUhTR2s0WGVEYjVNcXY4N1A0bFRTY29STU5aWEdabzZZRTN3RmVHdWpESWZBeVdMa0s2Z0M0T2l5NTM2SnBPdW90NVFSMngvR1owaEpjaXNqYkpadlh1bWdoUkNCNFJlNDNLNG82bkpLdXlRa2hMV1RjWWhMeFErNmFmMVlMYWIrdXhPNTdQTWdtZHJDWTBLMjJnUlJib1k5cnZiUGpsalB1cVhaeDNlN1BCVjdjYWZQVXo1US9HU2NVVTBFOG1XeHRBZFJsV1NzZ2VCVlNneHN0R0ZoSEE0aEdXeElWQVRxK1ZFdkIvT2wvdnQybVdseXlrMnNkOW85TVdRdlJ2Z21WU0RmVnpHOXdpOWJ3aHJiYWoyOVA1YjlPSnJMdXJ4dk1uYkd6ZUQ4bnk1a1JON09UTE02d2tubUphMHhEdW5lNEtPclc3OUl2b0lFZGtOOUVoajgxZ0NLMytCVHdncitFZnI4d2l6UjBkZkRVcmh0WVZwUlc4ekdpY09IWEdnbFNkeVl2TGtBck11SEhzVzg3Y1IyS0NpUlBTRkF1aFgxTFBOVTRJNjVJZ21SRjQ4cjBzbEdyOGVpRC9USlpiajFnbTYrdkRDQnlTQXpXbEVqRDNPd2kraVJTZEZuVGhlZGpIU0s3NjNSSVBuNlNlSlFyWlA3bkZCS2ZsaGxVZ1ZpMUo4UzhCNW1tekh4SG9yY3M5NHVkaTRJYjNwakFyZXlmNmZiZXZ2SnE3ZVFLdzgxckc3cENnekdTZUY1eDQ1clM3NzVRcVJUVDRLYkV1UkVBNHVDZFYvY1NxUnN6TVFadk1IZ3dvWVRpbUx6bGdEK1NjNXlocXFvc2NWSDV3SzlUMzkyTHlGM2ptLzl1L3ZlK2RBYVFFcGE5bStKdkJ4R2tMZGVKYUZrVWtSdndXWlJEeGllWVBYZUgzc1VmT25XQS9NNEZ5M3kzZ3ZxbXU0dnFhQm1LbmpRWTl4RzYrTHJuRCtBN1dVOFVQSU04UWpSSzFnUFFLWCthOWN2VDR3SFVuaVRjNXdwSmlvaUlNU3pLVHBjalFPS2hyMGNveE9XbmR5VUxlcTA9IiwiRW1haWwiOiJKS3psbTk5RnVTSWlrVm90U2o1djlDZTNwQTd4c0g2WnVxM1JoZ2IyNVlkSUZQekxWMkdTIiwiVXNlciI6InZwMWIrd1JjZEFXOFhvQktqZ29qSjJuZHJNTkQvOTNoMGZYZTBZQXZIMDBsS2c9PSIsIkNyZWF0ZWRBdCI6IjIwMjAtMDMtMDZUMTk6MDY6NDkuMzYyMjkzOTkyWiIsIkV4cGlyZXNPbiI6IjIwMjAtMDMtMDdUMTk6MDY6NDlaIn0=|1583521609|NnkxgSIJdiRv5EvbiJgRtNjtLrM='
    
    auth_cookie_header = f'_oauth2_proxy={auth_token}'
    s = requests.Session()
    s.headers.update({'cookie': auth_cookie_header})
    stac_client = StacClient(stac_url, session=s)

    for product in products:
        prefixes = form_prefixes(product, start_date, end_date=end_date)
        print(f'Will query {len(prefixes)} dates for product {product}')
        num_items = 0
        if not dry_run:
            try:
                for i, prefix in enumerate(prefixes):
                    num_items += update_metadata_entries(gcs_client, stac_client, bucket_name, prefix)
                    if i % 50 == 0 and i > 0:
                        print(f'\nAt {prefix}, added {num_items} items')
                    else:
                        print('.', end='', flush=True)
            except Exception as e:
                print("\nError occurred")
                print(e)
            finally:
                print(f"\nWhere you left off: {prefix}")

if __name__ == '__main__':
    entry()
    # EO_METADATA_SECRET = './config/geoanalytics-canada-e499c8180765.json'
    # EO_GCS_MTL_BUCKET = 'granule-gcs-mtl01'
    # # register at https://urs.earthdata.nasa.gov/home

    # gcs_client = storage.Client.from_service_account_json(EO_METADATA_SECRET)
    # # products = ['MOD09GQ.006']
    # # products = [
    # #     'MOD09GQ.006', 'MOD09Q1.006', 'MCD12Q1.006', 'MOD11A1.006',
    # #     'MOD11A2.006', 'MOD13Q1.006'
    # # ]
    # start_date = '2018-07-01'
    # end_date = '2018-07-02'

    # # stac_url = 'https://stac.geoanalytics.ca'
    # stac_url = 'http://localhost:8080'
    # auth_cookie = 'eyJBY2Nlc3NUb2tlbiI6ImhKZTBTdGhaT003cmtyeStDVnhjOU5Nc3diQlJTdUdFTzJ1YUFKckg2T2ErMkQwNHRLMHZ3NlZ0OUhHMEpOYXZ0Sk15UWdQM0s2dVNNamczaTY4eXR5SjlFczNKTU1Pd1JJS3NEZGxDd3AxZDNPdUlxVUZKaGMwNldEUDFTT3RzclROZzRGM0xSMjU5aWR0QWtmbTk3aGYxVWo0aUdQdGtPbGNUVHhJM3p6dCszMU9PaFZhaGYxWXFwSllvK0pyNWZmbmp3YUhPbCthRDJxdXkzWS9pTnRhVGl5VCtONlgzd08yMVBuZzhKeURnaXpnME5iY0Q2RzBxZDJVYnppekFGbVIrQWVrYXBad0VjNE9OT0Z2TVg5aWtxVmNrSGhPbE44L2Y2M1ZWcXhaQktMOTVlYW1JY3RZTFhNY0NVMjlyY0R5ZjZCb1cvbW1oTlo5bklSb09hd1ZXdXZOcXhDVGVwNnR0Y2syWFBxbXFWVWRvQnFUNWFpMEpzZnVQKzBkdFg2Q2pHTnJjNGEvUDRxeXV2c0NuTStXN3JrVUFOSVhTYzZvQjkzOGpvMUtqaEpQOFZkVC9ZWk96WU8zUXFVZUdmMCs2VkhTdlN6UG1Na3BDNmVRNlJzeHJteEU2Q0gvaDV0cU1RbEVqdjlYSWthS3VZa3JOS0RpOXROS2NZZTM1c0h5VjFFNEhEbjNvTFhhRjRHYVkzQmhqb2tGVytyYWhJZUF0YXdyTU0wcVhVUDlsUzJYMHZOMHhhSDZDSjN0cElqaFFPQUd0R2dJSWxXemlKeWh6UGNzRXBFWEdFakp3UG9NSzZCMXI1T3lDbUp6UHFMWjFFWGd0empaNHc2a3Z0bVN2UURRS1FadE80NzBqbm40dzBPci9SSDF2bVNvb09FWEd3alR6N0pDY0pQUmxnZ2RGd3NFZytydUxvVkZaL2R2K01wSmdheUx1WDY5MEFQOU9lK0VSN1VqY1NPeTIwZkxVc3VXbHFZSE5mQ3cxeFNvR0JwdmJ5TTk0bmwxZlljdXVZTzFFVFhYaXprVzd6NkFIYmRnZlFiTjB2Qzd6bUEvdk1FZlFJQlpBdkx4M1VCakQva1hETjc0MEhNM2h0OS9KeHVlaERmNFRPVzdSOXpvd05hbE5jNVNPVWdQdFIyVWZJMlRXYVdWSUhkb0VwSEc5YTV4dWkyWWZlN1VKRk85Q1NXaHhoN3drSk51ODlrVDVPdHErR0VMSFdkZnFaU0NKQ1BObWtvZmZDemJFYTc3SUlNTzdWb0NIYjlIQVE2U1lFUEFEWU83YTZEL2RpQTRoWm5YaG8yMHF2Z3J0eVZvYkJpdzQyS2t0S29vOGxxOFdBSWk0MHlMS3RXWHRodVdrZTRaKzErZVZDLysvWWRsZVBQQ2VVbC9YQlMvdWJWWFNmczdVUDJSQWdvOGdLdm44cnVCOXFyeXhiaHVEczNIZ2gxbjJqRDUzTHRyOUp0dXlxWkE9IiwiSURUb2tlbiI6Ik1EYTg4bVFlbkFWRFJhajZhQVNYdyt3TTdhQTRSbTlseGdJRm4vdld6OHU1Z2k3YW9Da3lMYmZKZzNjdWNScFdhV3dYOGpUWndHcWRIcDIyQW91bDU3elpKMXpEeHRXdnpraEFKdFNoWlUwT1AwS1FDOUY5cUhHT3p3aGtwb3llaU01QUJRNGZMbFRWSVQ1RDF6eXdza2ppeGFLZWVCVkZ2Q05uZ0k5aUhVamZhT3ZJRW1DbExGY08vN3JNQjRPRFR3NXBTR3cxR3k2T1JRWlREQlByZXNVbllxRkNJZTVJMHBtK1plaWh3T1RXU2srd1gwVjZsVDhNMGt6MG9HL2FVSkRIeFlHdVdrY0RjcTlJTGxVL2dwUlhhMlZZelJCYTFtOUt5cnZlSW8zZkhQc2ZIMCtITkk5V3BJbjRDSXBGUHRnVEZHMFVlT2pQVWh5L0E2TFRQOTR3OG8rUnZyMXh3cm9rWEc4dml0NXhiSk5BTHA1MWo1TkZJU3NYQzNPZGs4RzVEa3RISllJMWZhODJIZm14SWY5Nm1LZithN0RaUGx1bk43Y29DendMNXRhc25OZjVSUm1FNm1rMVg0TndkYW80VXhscWt5MXdIanh0YlRlM2VnZ1ZIZC9hRmxnckZJWXBNaGpwdzh0VDgrc3p3U2JPTVZtZ1E0L3NXNEJKS01tbEdWZlF3TEV2TlEzanpFdkoxNVNPdWxMWTZEazhvQzQ1RStweWFsYkdhVDZoWkN0TFNJUkpuVnErc081aWNsRndrb3Axb0hGUWphbEpEaGhqeXBqOURaYWpMcmZhMVN5cW1rRWVHaCtTOGNvWk1QdThQT0tlb21WK3lLVlB6ZTA0N042eVZRWTl6ZU5JRHdWUWhldHpacGpwU3JFVlR1Tm9yRHBOeTYxZmRnV0k0WWdPZ1Nlem5EUktTUFBoRkFzbTZDbjNxc09aYm1FUjhScUYxckQ4bDZlSjlrbjdyeDh6K1JKT0NKL0FGTk92S2Y2RFRlZVBQQ3NYdGw3d2llSEpQK1ZiblBLT3RaOHZsZ2pKVTN3Z2JnendEYnZObUxXdXBxNlgzQ1RaTllva0F4cjQ2b2trTDlWM0FBb1E5MUVMTnJwMVpqanlHYndBem9PZ2hkTnhkZWlWWnkzUHBlZlFETW5ybk1VTDUwM0F1R0RjeGY1bjl1bVRuaC9QTjhzK0Q2S3AwOEozZjlmaElrTC9SN0JHRzhsRkVzT3U5djdNRC9rOHp6RU9PK1RyYUJVbEtPc0dzL1lLMU5tbVlWeDJ3OGJIVmRNdmIzdkJWb3dZRU5EeEpkd2xQdnFlaWlHUTJNaEhjZ1pVRWVoUGQ4NnE4RktsV2R3V0ljNWdHRlN5SVZoZS9VbE56QWZZV3QyTi9NV2JqZkhFU241TFQrNSs0cTN3WEhqVktzU0dTYS9oOTRTUzJkVnFiR3U1THpxenlaWHRvN2FaM3JYbVI3aC9Ld289IiwiRW1haWwiOiJEamZrc0pJMFJJVnJWa1VkQ1ZWVGVvVXljQlpKa1lVYk5tNXI2NGVoOHliVUNYYnVTS1VNIiwiVXNlciI6Inphc01KS0FqaTZnVjlxbjlQSEpiTlk1NHhaTzJsc2M4ZldPQWR4UDE4VTdROXc9PSIsIkNyZWF0ZWRBdCI6IjIwMjAtMDEtMTRUMjM6NDE6MDIuNTg4ODk0ODI3WiIsIkV4cGlyZXNPbiI6IjIwMjAtMDEtMTVUMjM6NDE6MDJaIn0=|1579045262|kIEhFeg4lCjtnyd4P2vf4YH4Xfk='
    # #cookie = { '_oauth2_proxy': auth_cookie }
    # auth_cookie_header = f'_oauth2_proxy={auth_cookie}'
    # #stac_url = 'http://localhost:8080'
    # s = requests.Session()
    # s.headers.update({'cookie': auth_cookie_header})
    # stac_client = StacClient(stac_url, session=s)

    # for product in products:
    #     prefixes = form_prefixes(product, start_date, end_date=end_date)
    #     print(f'Queried {len(prefixes)} items')
    #     try:
    #         for prefix in prefixes:
    #             update_metadata_entries(prefix)

    #     except Exception as e:
    #         print("Error occurred")
    #         print(e)
    #     finally:
    #         print(f"Where you left off: {prefix}")