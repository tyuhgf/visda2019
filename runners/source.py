import tensorflow as tf
from functools import partial

from trainer import Trainer
from tester import Tester
from models import SourceTrainStep, SourceTestStep, get_backbone
from utils import DOMAINS, N_CLASSES, read_paths_and_labels, make_dataset, make_domain_dataset
from preprocessor import Preprocessor

RAW_DATA_PATH = '/content/data/raw'
LOG_PATH = '/content/data/logs'
BATCH_SIZE = 32
IMAGE_SIZE = 64
BACKBONE_NAME = 'mobilenet_v2'
CONFIG = [
    {'method': 'keras', 'mode': 'tf'},
    {'method': 'resize', 'height': IMAGE_SIZE, 'width': IMAGE_SIZE}
]


def build_model(image_size, n_classes, name):
    return tf.keras.Sequential([
        get_backbone(name)(
            input_shape=(image_size, image_size, 3),
            include_top=False,
            weights='imagenet'
        ),
        tf.keras.layers.GlobalAveragePooling2D(),
        tf.keras.layers.Dense(4096, activation='relu'),
        tf.keras.layers.Dense(n_classes, input_shape=(4096,), activation='softmax')
    ])


build_model_lambda = partial(build_model, image_size=IMAGE_SIZE, n_classes=N_CLASSES, name=BACKBONE_NAME)

paths_and_labels = read_paths_and_labels(RAW_DATA_PATH, DOMAINS, 3)
target_paths = paths_and_labels['target']['train']['paths'] + paths_and_labels['target']['test']['paths']
target_labels = paths_and_labels['target']['train']['labels'] + paths_and_labels['target']['test']['labels']
train_dataset = iter(make_dataset(
    source_paths=paths_and_labels['source']['train']['paths'],
    source_labels=paths_and_labels['source']['train']['labels'],
    source_config=CONFIG,
    target_paths=target_paths,
    target_labels=target_labels,
    target_config=CONFIG,
    batch_size=BATCH_SIZE
))
validate_dataset = iter(make_dataset(
    source_paths=paths_and_labels['source']['test']['paths'],
    source_labels=paths_and_labels['source']['test']['labels'],
    source_config=CONFIG,
    target_paths=target_paths,
    target_labels=target_labels,
    target_config=CONFIG,
    batch_size=BATCH_SIZE
))

train_step = SourceTrainStep(
    build_model_lambda=build_model_lambda,
    domains=DOMAINS,
    n_frozen_layers=230,
    learning_rate=0.001
)
trainer = Trainer(
    train_step=train_step,
    n_iterations=500,
    n_log_iterations=100,
    n_save_iterations=500,
    n_validate_iterations=10,
    log_path=LOG_PATH,
    restore_model_flag=False,
    restore_optimizer_flag=False
)
trainer(validate_dataset, train_dataset)

train_step = SourceTrainStep(
    build_model_lambda=build_model_lambda,
    domains=DOMAINS,
    n_frozen_layers=0,
    learning_rate=0.0001
)
trainer = Trainer(
    train_step=train_step,
    n_iterations=1000,
    n_log_iterations=100,
    n_save_iterations=1000,
    n_validate_iterations=10,
    log_path=LOG_PATH,
    restore_model_flag=True,
    restore_optimizer_flag=False
)
trainer(train_dataset, validate_dataset)

test_dataset = iter(make_domain_dataset(
    paths=target_paths,
    labels=target_labels,
    preprocessor=Preprocessor(CONFIG),
    batch_size=BATCH_SIZE
))
test_step = SourceTestStep(build_model_lambda, domains=DOMAINS)
tester = Tester(test_step=test_step, log_path=LOG_PATH)
tester(test_dataset)
# >>> acc: 9.74910e-02
