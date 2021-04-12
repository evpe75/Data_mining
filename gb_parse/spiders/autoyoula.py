import scrapy
from .. db import DbMongoSaver

class AutoyoulaSpider(scrapy.Spider):
    name = "autoyoula"
    allowed_domains = ["auto.youla.ru"]
    start_urls = ["https://auto.youla.ru/"]

    def _get_follow(self, response, select_str, callback, **kwargs):
        for a in response.css(select_str):
            url = a.attrib.get("href")
            yield response.follow(url, callback=callback, **kwargs)

    def parse(self, response):
        yield from self._get_follow(
            response, "div.TransportMainFilters_brandsList__2tIkv a.blackLink", self.brand_parse
        )

    def brand_parse(self, response):
        yield from self._get_follow(
            response, "div.Paginator_block__2XAPy a.Paginator_button__u1e7D", self.brand_parse
        )
        yield from self._get_follow(
            response,
            "article.SerpSnippet_snippet__3O1t2 a.SerpSnippet_name__3F7Yu",
            self.car_parse,
        )

    def car_parse(self, response):
        # Название объявления
        # Список фото объявления(ссылки)
        # Список характеристик
        # Описание объявления
        # ссылка на автора объявления
        # дополнительно попробуйте вытащить телефона
        data = {
            "url": response.url,
            "title": response.css("div.AdvertCard_advertTitle__1S1Ak::text").extract_first(),
            "price": float(
                response.css("div.AdvertCard_price__3dDCr::text")
                .extract_first()
                .replace("\u2009", "")
            ),
            "text": response.css("div.AdvertCard_descriptionInner__KnuRi::text").extract_first(),
            #!!! не удалось получить продавца и его телефон, не нашел откуда данные приходят
            #"seller": response.css("a.SellerInfo_name__3Iz2N").extract_first().attrib.get("href"),
            # Характеристики удалось только через xpath получить, не понял как через функцию css
            # доступиться до текста названия характеристики и ее значения
            "characteristics":
                dict(zip(response.xpath('//div[@class = "AdvertSpecs_label__2JHnS"]/text()').extract(),
                         response.xpath('//div[@class = "AdvertSpecs_data__xK2Qx"]/text()|'
                                        '//div[@class = "AdvertSpecs_data__xK2Qx AdvertSpecs_isCrashed__2DKyG"]/text()|'
                                        '//div[@class = "AdvertSpecs_data__xK2Qx"]/a/text()').extract())),
            "imgs": [img.attrib.get('src') for img in response.css("img.PhotoGallery_photoImage__2mHGn")]

        }

        saver = DbMongoSaver()
        saver.save_data(data)
