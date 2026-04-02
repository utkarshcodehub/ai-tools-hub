from fastapi import APIRouter
from typing import List
from models import Category
from data_loader import get_categories

router = APIRouter()


@router.get("/", response_model=List[Category])
def list_categories():
    return get_categories()