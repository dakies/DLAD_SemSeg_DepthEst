import torch
import torch.nn.functional as F

from mtl.models.model_parts import Encoder, get_encoder_channel_counts, ASPP, DecoderDeeplabV3p


class ModelDeepLabV3PlusBranched(torch.nn.Module):
    def __init__(self, cfg, outputs_desc):
        super().__init__()
        self.outputs_desc = outputs_desc
        ch_out = sum(outputs_desc.values())

        self.encoder = Encoder(
            cfg.model_encoder_name,
            pretrained=True,
            zero_init_residual=True,
            replace_stride_with_dilation=(False, False, True),
        )
        print('Branched Model')
        ch_out_encoder_bottleneck, ch_out_encoder_4x = get_encoder_channel_counts(cfg.model_encoder_name)

        self.aspp_semseg = ASPP(ch_out_encoder_bottleneck, 256)
        self.decoder_semseg = DecoderDeeplabV3p(256, ch_out_encoder_4x, ch_out)

        self.aspp_depth = ASPP(ch_out_encoder_bottleneck, 256)
        self.decoder_depth = DecoderDeeplabV3p(256, ch_out_encoder_4x, ch_out)

    def forward(self, x):
        input_resolution = (x.shape[2], x.shape[3])

        features = self.encoder(x)

        # Uncomment to see the scales of feature pyramid with their respective number of channels.
        print(", ".join([f"{k}:{v.shape[1]}" for k, v in features.items()]))

        lowest_scale = max(features.keys())

        features_lowest = features[lowest_scale]
        # Semseg
        features_semseg = self.aspp_semseg(features_lowest)
        predictions_4x_semseg, _ = self.decoder_semseg(features_semseg, features[4])
        predictions_1x_semseg = F.interpolate(predictions_4x_semseg, size=input_resolution, mode='bilinear',
                                              align_corners=False)

        # Depth
        features_depth = self.aspp_depth(features_lowest)
        predictions_4x_depth, _ = self.decoder_depth(features_depth, features[4])
        predictions_1x_depth = F.interpolate(predictions_4x_depth, size=input_resolution, mode='bilinear',
                                             align_corners=False)

        predictions_1x = torch.cat((predictions_1x_semseg, predictions_1x_depth), 1)
        out = {}
        offset = 0

        for task, num_ch in self.outputs_desc.items():
            out[task] = predictions_1x[:, offset:offset + num_ch, :, :]
            offset += num_ch

        return out
