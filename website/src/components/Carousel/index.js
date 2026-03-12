import React from "react";
import Slider from "react-slick";
import "slick-carousel/slick/slick.css";
import "slick-carousel/slick/slick-theme.css";
import ChevronRightIcon from "@material-ui/icons/ChevronRight";
import ChevronLeftIcon from "@material-ui/icons/ChevronLeft";
import "../../css/carousel.css";

export default function Carousel({ slides }) {
    const sliderRef = React.useRef(null);

    var settings = {
        dots: true,
        arrows: true,
        infinite: true,
        speed: 1000,
        autoplay: true,
        autoplaySpeed: 8000,
        slidesToShow: 1,
        slidesToScroll: 1,
        nextArrow: <ChevronRightIcon className="slick-next" />,
        prevArrow: <ChevronLeftIcon className="slick-prev" />,
    };

    return (
        <section className="carouselSection">
            <div className="container">
                <div className="slider-container">
                    <Slider ref={sliderRef} {...settings}>
                        {slides.map((slide, index) => (
                            <div key={index}>
                                <a href={slide.link} target="_blank" rel="noopener noreferrer" className="carouselSlide">
                                    <div className="carouselText">
                                        <h3 className="carouselTitle">{slide.title}</h3>
                                        <p className="carouselDescription" dangerouslySetInnerHTML={{ __html: slide.description }} />
                                    </div>
                                    <div className="carouselImageWrap">
                                        <img src={slide.image} alt={slide.title} />
                                    </div>
                                </a>
                            </div>
                        ))}
                    </Slider>
                </div>

            </div>
        </section>
    );
}